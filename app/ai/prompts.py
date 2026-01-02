"""
Prompt templates for AI content generation.
Structured prompts for blog posts, SEO metadata, etc.
"""

from typing import Optional


# HTML component templates for AI to use
HTML_COMPONENTS = """
=== DOSTĘPNE KOMPONENTY HTML ===

1. INFO-BOX (ważne informacje, podstawa prawna):
<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-balance-scale"></i> Tytuł</div>
<p>Treść informacji.</p>
</div>
Kolory: blue (informacja), yellow (uwaga), green (pozytywne), orange (ostrzeżenie)
Ikony: fa-balance-scale (prawo), fa-lightbulb (wskazówka), fa-exclamation-triangle (uwaga), fa-clock (termin), fa-calendar-alt (data)

2. HIGHLIGHT-BOX (kluczowe dane, statystyki):
<div class="highlight-box">
<div class="highlight-grid">
<div class="highlight-item">
<span class="highlight-label">Etykieta</span>
<span class="highlight-value">Wartość</span>
</div>
</div>
</div>

3. CARD-GRID (karty obok siebie):
<div class="card-grid">
<div class="info-card">
<h3><i class="fas fa-icon"></i> Tytuł karty</h3>
<p>Treść karty.</p>
</div>
</div>

4. TWO-COLUMNS (porównania, pros/cons):
<div class="two-columns">
<div class="column">
<h4 class="column-title green"><i class="fas fa-check-circle"></i> Pozytywne</h4>
<ul><li>Element</li></ul>
</div>
<div class="column">
<h4 class="column-title orange"><i class="fas fa-exclamation-circle"></i> Negatywne</h4>
<ul><li>Element</li></ul>
</div>
</div>

5. TIPS-LIST (wskazówki krok po kroku):
<div class="tips-list">
<div class="tip-item">
<span class="tip-number">1</span>
<div class="tip-content">
<strong>Tytuł kroku</strong>
<p>Opis kroku.</p>
</div>
</div>
</div>

6. SECTION-DIVIDER (rozdzielacz sekcji):
<hr class="section-divider" />

7. DISCLAIMER-BOX (zastrzeżenie prawne na końcu):
<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji.</p>
</div>
"""


def build_system_prompt(
    expertise: str,
    persona: Optional[str],
    tone: str,
    target_audience: Optional[str] = None
) -> str:
    """
    Build system prompt for Claude based on agent configuration.

    Args:
        expertise: Domain expertise (e.g., "prawo", "marketing", "tech")
        persona: Agent persona description
        tone: Writing tone (professional, casual, friendly)
        target_audience: Optional target audience description

    Returns:
        System prompt string
    """
    prompt = f"""Jesteś ekspertem w dziedzinie: {expertise}"""

    if persona:
        prompt += f"\n\nTwoja persona:\n{persona}"

    prompt += f"\n\nTon wypowiedzi: {tone}"

    if target_audience:
        prompt += f"\nPiszesz dla: {target_audience}"

    prompt += """

ZASADY PISANIA:

1. **Struktura SEO:**
   - Używaj hierarchii nagłówków HTML (<h2>, <h3>)
   - Keyword musi pojawić się w pierwszych 100 słowach
   - Akapity max 3-4 zdania dla czytelności
   - Używaj list <ul>/<li> dla lepszego skanowania

2. **Content Quality:**
   - Pisz naturalnie, unikaj keyword stuffing
   - Używaj synonimów i pokrewnych terminów
   - Dodawaj konkretne przykłady i dane
   - Podawaj podstawy prawne gdzie to możliwe

3. **Engagement:**
   - Zacznij od mocnego hooka
   - Używaj pytań retorycznych
   - Dodaj praktyczne wskazówki
   - Zakończ wyraźnym podsumowaniem

4. **Format - WAŻNE:**
   - Pisz w czystym HTML (NIE Markdown!)
   - Używaj <strong> dla kluczowych punktów
   - Używaj <em> dla podkreśleń
   - NIE używaj # ani ** - to Markdown!
   - Używaj specjalnych komponentów HTML poniżej
"""

    prompt += HTML_COMPONENTS

    return prompt


def build_post_generation_prompt(
    topic: str,
    keyword: Optional[str],
    length: str,
    sources_content: Optional[str] = None,
    additional_context: Optional[str] = None
) -> str:
    """
    Build prompt for blog post generation.

    Args:
        topic: Post topic/title
        keyword: Target SEO keyword
        length: Post length (short/medium/long/very_long)
        sources_content: Optional source content to reference
        additional_context: Optional additional context

    Returns:
        Generation prompt string
    """
    # Word count targets
    word_counts = {
        "short": "500-700",
        "medium": "1000-1500",
        "long": "2000-3000",
        "very_long": "3000-5000"
    }
    target_words = word_counts.get(length, "1000-1500")

    prompt = f"""Napisz profesjonalny artykuł blogowy na temat:

TEMAT: {topic}"""

    if keyword:
        prompt += f"\nGŁÓWNE KEYWORD SEO: {keyword}"

    prompt += f"""
DŁUGOŚĆ DOCELOWA: {target_words} słów
FORMAT: Czysty HTML z komponentami CSS (NIE Markdown!)

"""

    if sources_content:
        prompt += f"""ŹRÓDŁA DO WYKORZYSTANIA:
{sources_content}

Wykorzystaj powyższe źródła jako inspirację i fakty, ale pisz swoimi słowami.

"""

    if additional_context:
        prompt += f"""DODATKOWY KONTEKST:
{additional_context}

"""

    prompt += """WYMAGANA STRUKTURA HTML:

1. NA POCZĄTKU - Info-box z podstawą prawną (jeśli dotyczy):
<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-balance-scale"></i> Podstawa prawna</div>
<p><strong>Nazwa ustawy/aktu</strong> - artykuły.</p>
</div>

2. SEKCJE (3-5 sekcji z <h2>):
   - Każda sekcja skupiona na jednym aspekcie
   - Rozdzielaj sekcje: <hr class="section-divider" />
   - Używaj <h3> dla podsekcji
   - Używaj <ul><li> dla list

3. WIZUALNE ELEMENTY (użyj min. 3-4 różnych):
   - highlight-box dla kluczowych danych/statystyk
   - card-grid dla porównań opcji
   - two-columns dla pros/cons
   - tips-list dla kroków/wskazówek
   - info-box yellow dla ostrzeżeń
   - info-box green dla pozytywów

4. NA KOŃCU - ZAWSZE dodaj disclaimer-box:
<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji.</p>
</div>

WAŻNE ZASADY:
- Pisz w czystym HTML, NIE używaj Markdown (żadnych # ani **)
- Używaj <strong> zamiast **tekst**
- Używaj <h2> zamiast ## Nagłówek
- Używaj <p> dla paragrafów
- NIE zaczynaj od <h1> - tytuł jest osobno
- Rozpocznij od info-box lub od wstępu z <p>
- Używaj polskiego języka wysokiej jakości
- Wprowadzaj keyword naturalnie w treści
- Pisz przystępnie ale profesjonalnie
"""

    return prompt


def build_meta_title_prompt(content: str, keyword: Optional[str]) -> str:
    """
    Build prompt for meta title generation.

    Args:
        content: Post content
        keyword: Target keyword

    Returns:
        Prompt for meta title
    """
    prompt = f"""Na podstawie poniższego artykułu, wygeneruj SEO-friendly meta title.

**Wymagania:**
- Maksymalnie 60 znaków
- Zawiera główny keyword: {keyword if keyword else "wyciągnij z treści"}
- Przyciąga uwagę
- Jasno komunikuje temat
- Nie używaj clickbaitu

**Artykuł:**
{content[:1000]}...

Odpowiedz TYLKO samym tytułem, bez cudzysłowów ani dodatkowego tekstu."""

    return prompt


def build_meta_description_prompt(content: str, keyword: Optional[str]) -> str:
    """
    Build prompt for meta description generation.

    Args:
        content: Post content
        keyword: Target keyword

    Returns:
        Prompt for meta description
    """
    prompt = f"""Na podstawie poniższego artykułu, wygeneruj SEO-friendly meta description.

**Wymagania:**
- Maksymalnie 160 znaków
- Zawiera główny keyword: {keyword if keyword else "wyciągnij z treści"}
- Zachęca do kliknięcia
- Jasno komunikuje wartość artykułu
- Kończy się CTA lub zachętą

**Artykuł:**
{content[:1000]}...

Odpowiedz TYLKO samym opisem, bez cudzysłowów ani dodatkowego tekstu."""

    return prompt


def build_keywords_extraction_prompt(content: str) -> str:
    """
    Build prompt for keyword extraction.

    Args:
        content: Post content

    Returns:
        Prompt for keyword extraction
    """
    prompt = f"""Przeanalizuj poniższy artykuł i wyciągnij 5-10 najważniejszych słów kluczowych (keywords).

**Wymagania:**
- Słowa/frazy 1-3 wyrazowe
- Istotne dla SEO
- Naturalne dla treści
- Posortowane od najważniejszych

**Artykuł:**
{content[:2000]}...

Odpowiedz w formacie JSON array, np: ["keyword1", "keyword2", "keyword3"]
TYLKO JSON, bez dodatkowego tekstu."""

    return prompt
