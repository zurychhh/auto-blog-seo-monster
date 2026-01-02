# Plan: Automatyczne Planowanie Postów AI

## Cel
System automatycznego generowania i publikowania postów SEO na tematy prawne w Polsce, z konfigurowalnymi interwałami czasowymi.

---

## 1. Konfiguracja Interwałów (Admin Panel)

### 1.1 Nowy model `ScheduleConfig`
```python
# app/models/schedule.py
class ScheduleConfig(Base):
    __tablename__ = "schedule_configs"

    id: UUID
    agent_id: UUID (FK -> agents)

    # Interwał publikacji
    interval: Enum["daily", "every_3_days", "weekly", "biweekly"]

    # Godzina publikacji (0-23)
    publish_hour: int = 10  # Domyślnie 10:00

    # Status
    is_active: bool = True
    last_run_at: datetime | None
    next_run_at: datetime | None

    # Konfiguracja SEO
    auto_publish: bool = True  # Auto-publikuj lub zostaw jako draft
    target_keywords: List[str]  # Lista preferowanych tematów
    exclude_keywords: List[str]  # Lista wykluczonych tematów

    created_at: datetime
    updated_at: datetime
```

### 1.2 Mapowanie interwałów na cron
```python
INTERVAL_CRON_MAP = {
    "daily": "0 10 * * *",        # Codziennie o 10:00
    "every_3_days": "0 10 */3 * *", # Co 3 dni o 10:00
    "weekly": "0 10 * * 1",        # W poniedziałki o 10:00
    "biweekly": "0 10 1,15 * *"    # 1 i 15 każdego miesiąca
}
```

### 1.3 API Endpoints
```
POST   /api/v1/schedules           - Utwórz harmonogram
GET    /api/v1/schedules           - Lista harmonogramów
GET    /api/v1/schedules/{id}      - Szczegóły harmonogramu
PUT    /api/v1/schedules/{id}      - Aktualizuj harmonogram
DELETE /api/v1/schedules/{id}      - Usuń harmonogram
POST   /api/v1/schedules/{id}/run  - Uruchom ręcznie
```

---

## 2. Topic Discovery Service (Web Search)

### 2.1 Nowy serwis `TopicDiscoveryService`
```python
# app/services/topic_discovery.py
class TopicDiscoveryService:
    """Odkrywanie trendujących tematów prawnych w Polsce."""

    async def discover_trending_topics(
        self,
        category: str = "prawo",  # prawo, prawo-cywilne, prawo-pracy, etc.
        count: int = 5
    ) -> List[TrendingTopic]:
        """
        Źródła tematów:
        1. Google Trends API (pl)
        2. RSS z polskich portali prawnych
        3. Web scraping nagłówków (prawo.pl, infor.pl, gazetaprawna.pl)
        4. Analiza zapytań z poprzednich postów (internal analytics)
        """
        pass

    async def validate_topic_seo_potential(
        self,
        topic: str
    ) -> TopicSEOScore:
        """
        Ocena potencjału SEO tematu:
        - Wolumen wyszukiwań (estimated)
        - Konkurencyjność
        - Sezonowość
        - Relevance score
        """
        pass
```

### 2.2 Źródła tematów prawnych
```python
POLISH_LEGAL_SOURCES = [
    # RSS Feeds
    "https://www.prawo.pl/rss",
    "https://www.infor.pl/prawo/rss",
    "https://gazetaprawna.pl/rss",
    "https://www.rp.pl/prawo/rss",

    # Google News PL - prawo
    "https://news.google.com/rss/search?q=prawo+polska&hl=pl&gl=PL&ceid=PL:pl",

    # Serwisy prawne
    "https://sip.lex.pl",  # LEX
    "https://legalis.pl",
]

LEGAL_CATEGORIES = [
    "prawo cywilne",
    "prawo pracy",
    "prawo konsumenckie",
    "prawo rodzinne",
    "prawo spadkowe",
    "prawo najmu",
    "prawo autorskie",
    "RODO / ochrona danych",
]
```

### 2.3 Struktura TrendingTopic
```python
@dataclass
class TrendingTopic:
    title: str
    category: str
    source: str
    source_url: str
    discovered_at: datetime

    # SEO metrics
    search_volume_estimate: int  # 0-100 scale
    competition_level: str  # low, medium, high
    trending_score: float  # 0-1

    # Generated
    suggested_keywords: List[str]
    suggested_title: str
    suggested_outline: List[str]
```

---

## 3. Enhanced SEO Optimization

### 3.1 Rozszerzony `SEOService`
```python
# Nowe metody w app/services/seo_service.py

async def research_keywords(
    self,
    topic: str,
    language: str = "pl"
) -> KeywordResearchResult:
    """
    Badanie słów kluczowych:
    - Main keyword
    - LSI keywords (Latent Semantic Indexing)
    - Long-tail keywords
    - Question keywords (People Also Ask)
    """
    pass

async def analyze_serp_competition(
    self,
    keyword: str
) -> SERPAnalysis:
    """
    Analiza konkurencji w SERP:
    - Top 10 wyników
    - Średnia długość contentu
    - Wymagane H2/H3
    - Featured snippets
    """
    pass

def calculate_seo_score(
    self,
    content: str,
    target_keyword: str
) -> SEOScore:
    """
    Kompleksowa ocena SEO:
    - Title optimization (0-100)
    - Keyword density (0-100)
    - Content length (0-100)
    - Heading structure (0-100)
    - Readability (0-100)
    - Internal linking potential (0-100)
    - Overall score (0-100)
    """
    pass
```

### 3.2 Nowy prompt dla maksymalnego SEO
```python
def build_seo_optimized_prompt(
    topic: str,
    main_keyword: str,
    lsi_keywords: List[str],
    target_word_count: int,
    serp_analysis: SERPAnalysis,
    competitor_outlines: List[str]
) -> str:
    """
    Zaawansowany prompt SEO:
    - Analiza konkurencji
    - Wymagane sekcje
    - Keyword placement strategy
    - Featured snippet optimization
    - E-E-A-T signals (Experience, Expertise, Authority, Trust)
    """
    pass
```

---

## 4. Auto-Publish Workflow

### 4.1 Nowy Celery Task
```python
# app/tasks/auto_publish_tasks.py

@celery_app.task
def auto_generate_and_publish(schedule_id: str):
    """
    Pełny workflow automatycznej publikacji:

    1. DISCOVERY
       - Pobierz trending topics
       - Wybierz najlepszy temat (SEO score + unikalność)
       - Sprawdź czy temat nie był już poruszany

    2. RESEARCH
       - Keyword research
       - SERP analysis
       - Competitor content analysis

    3. GENERATION
       - Wygeneruj post z maksymalnym SEO
       - Wygeneruj meta tags
       - Wygeneruj schema markup

    4. VALIDATION
       - Sprawdź SEO score (min. 80/100)
       - Sprawdź unikalność (plagiarism check)
       - Sprawdź readability

    5. PUBLISH
       - Ustaw status na 'published'
       - Ustaw published_at
       - Wyślij do sitemap
       - (Opcjonalnie) Social media share

    6. REPORT
       - Zapisz raport z generacji
       - Wyślij notyfikację (email/slack)
    """
    pass
```

### 4.2 Celery Beat Schedule Update
```python
# Dodaj do celery_app.py beat_schedule

"auto-publish-scheduled": {
    "task": "app.tasks.auto_publish_tasks.process_auto_publish_schedules",
    "schedule": crontab(minute="0", hour="*"),  # Co godzinę
},
```

---

## 5. Admin Panel UI (Frontend)

### 5.1 Nowa strona `/admin/schedules`
```svelte
<!-- src/routes/admin/schedules/+page.svelte -->

<script>
  // Komponenty:
  // - Lista aktywnych harmonogramów
  // - Formularz tworzenia/edycji
  // - Historia publikacji
  // - Preview następnego posta
</script>

<!-- UI Elements -->
- Dropdown: Interwał (Codziennie, Co 3 dni, Co tydzień, Co 2 tygodnie)
- Time picker: Godzina publikacji
- Toggle: Auto-publikuj / Zostaw jako draft
- Tags input: Preferowane tematy
- Tags input: Wykluczone tematy
- Button: Uruchom teraz
- Calendar: Podgląd planowanych publikacji
```

### 5.2 Dashboard z statystykami
```
- Liczba automatycznych publikacji (tydzień/miesiąc)
- Średni SEO score
- Top performing posts
- Upcoming scheduled posts
```

---

## 6. Struktura plików do utworzenia

```
blog-backend/backend/app/
├── models/
│   └── schedule.py           # NEW - ScheduleConfig model
├── schemas/
│   └── schedule.py           # NEW - Pydantic schemas
├── api/
│   └── schedules.py          # NEW - API endpoints
├── services/
│   ├── topic_discovery.py    # NEW - Topic discovery
│   └── seo_service.py        # UPDATE - Enhanced SEO
├── tasks/
│   └── auto_publish_tasks.py # NEW - Auto-publish workflow
└── ai/
    └── prompts.py            # UPDATE - SEO-optimized prompts

src/routes/admin/
├── schedules/
│   ├── +page.svelte          # NEW - Schedule management
│   └── +page.server.ts       # NEW - Server-side data
└── +layout.svelte            # UPDATE - Add nav link
```

---

## 7. Kolejność implementacji

### Faza 1: Backend Core (1-2 dni)
1. [ ] Model `ScheduleConfig` + migracja
2. [ ] Schemas dla schedule
3. [ ] API endpoints `/schedules`
4. [ ] Basic Celery task

### Faza 2: Topic Discovery (1-2 dni)
1. [ ] `TopicDiscoveryService`
2. [ ] RSS adapter dla polskich źródeł
3. [ ] Google News integration
4. [ ] Topic scoring algorithm

### Faza 3: Enhanced SEO (1 dzień)
1. [ ] Rozszerzenie `SEOService`
2. [ ] Keyword research
3. [ ] SEO score calculation
4. [ ] Updated prompts

### Faza 4: Auto-Publish Workflow (1 dzień)
1. [ ] Full auto-publish task
2. [ ] Validation pipeline
3. [ ] Celery beat integration
4. [ ] Notifications

### Faza 5: Admin UI (1 dzień)
1. [ ] `/admin/schedules` page
2. [ ] Schedule form
3. [ ] Calendar preview
4. [ ] Statistics dashboard

---

## 8. Przykład użycia

```bash
# 1. Admin tworzy harmonogram w panelu
POST /api/v1/schedules
{
  "agent_id": "uuid",
  "interval": "weekly",
  "publish_hour": 10,
  "auto_publish": true,
  "target_keywords": ["prawo najmu", "prawa konsumenta"],
  "exclude_keywords": ["karne", "podatkowe"]
}

# 2. System automatycznie:
# - Poniedziałek 10:00: Szuka trending topics
# - Wybiera: "Nowe przepisy o najmie 2025"
# - Generuje 2000+ słów, SEO score 85/100
# - Publikuje automatycznie
# - Wysyła raport email

# 3. Post pojawia się na /blog w sekcji "Baza Wiedzy"
```

---

## 9. Metryki sukcesu

- **SEO Score**: Minimum 80/100 dla każdego posta
- **Keyword Density**: 1-2% dla main keyword
- **Readability**: Flesch score 50-70 (przystępny)
- **Word Count**: 1500-3000 słów
- **Unique Content**: 100% (brak plagiatów)
- **Publication Success Rate**: >95%

---

*Plan utworzony: 2025-12-16*
*Szacowany czas implementacji: 5-7 dni roboczych*
