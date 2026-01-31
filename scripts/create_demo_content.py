#!/usr/bin/env python3
"""
Create demo agent and post for Legitio.pl
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import AsyncSessionLocal
from app.models.agent import Agent
from app.models.post import Post
from app.models.tenant import Tenant
from sqlalchemy import select
from datetime import datetime


async def create_demo_content():
    """Create demo agent and post."""
    async with AsyncSessionLocal() as db:
        # Get Legitio tenant
        result = await db.execute(
            select(Tenant).where(Tenant.slug == "legitio")
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            print("❌ Legitio tenant not found. Run setup_legitio_tenant.py first.")
            return

        print(f"✅ Found tenant: {tenant.name} (ID: {tenant.id})")

        # Check if demo agent already exists
        result = await db.execute(
            select(Agent).where(
                Agent.tenant_id == tenant.id,
                Agent.name == "Ekspert Prawa Cywilnego"
            )
        )
        agent = result.scalar_one_or_none()

        if not agent:
            # Create demo agent
            agent = Agent(
                tenant_id=tenant.id,
                name="Ekspert Prawa Cywilnego",
                expertise="prawo",
                persona="Jestem ekspertem prawa cywilnego, specjalizuję się w tematyce najmu, konsumenckiej i rodzinnej. Piszę przystępne artykuły dla osób bez wykształcenia prawniczego.",
                tone="professional",
                post_length="long",
                workflow="draft",
                settings={"language": "pl"}
            )
            db.add(agent)
            await db.commit()
            await db.refresh(agent)
            print(f"✅ Agent created: {agent.name} (ID: {agent.id})")
        else:
            print(f"✅ Agent already exists: {agent.name} (ID: {agent.id})")

        # Check if demo post already exists
        result = await db.execute(
            select(Post).where(
                Post.agent_id == agent.id,
                Post.slug == "prawo-najmu-w-polsce-kompletny-przewodnik-2024"
            )
        )
        post = result.scalar_one_or_none()

        if not post:
            # Create demo post
            post_content = """
# Prawo Najmu w Polsce - Kompletny Przewodnik 2024

Wynajem mieszkania to częsta forma korzystania z nieruchomości w Polsce. Czy wiesz jednak, jakie prawa przysługują Ci jako najemcy? W tym artykule omówimy najważniejsze aspekty prawa najmu, abyś mógł swobodnie poruszać się w tej tematyce.

## Podstawy prawne najmu mieszkania

Umowa najmu jest uregulowana w **Kodeksie cywilnym** (art. 659-692). To właśnie tam znajdziesz wszystkie przepisy dotyczące praw i obowiązków wynajmującego oraz najemcy.

### Forma umowy najmu

Czy umowa najmu musi być zawarta na piśmie? To zależy:
- **Najem do 1 roku** - może być zawarty ustnie
- **Najem powyżej 1 roku** - wymaga formy pisemnej pod rygorem nieważności
- **Najem okazjonalny** - wymaga formy pisemnej i aktu notarialnego

**Ważne**: Nawet jeśli umowa ustna jest prawnie dopuszczalna, zawsze warto zawrzeć umowę na piśmie. Dzięki temu unikniesz późniejszych sporów o warunki najmu.

## Najważniejsze prawa najemcy

### 1. Prawo do spokojnego korzystania z lokalu

Jako najemca masz prawo do **niezakłóconego** korzystania z wynajmowanego mieszkania. Wynajmujący nie może:
- Wchodzić do mieszkania bez Twojej zgody
- Zakłócać Twojego spokoju
- Ingerować w sposób użytkowania lokalu (o ile jest zgodny z umową)

### 2. Prawo do napraw i utrzymania lokalu

**Wynajmujący jest zobowiązany** do utrzymania lokalu w stanie przydatnym do umówionego użytku. Oznacza to, że:
- Musi naprawiać usterki wynikające ze zwykłego zużycia (np. uszkodzone grzejniki, nieszczelne okna)
- Ponosi koszty większych remontów
- Musi zapewnić dostęp do podstawowych mediów

**Ty jako najemca** odpowiadasz za:
- Drobne naprawy związane ze zwykłym użytkowaniem (np. wymiana żarówek)
- Utrzymanie lokalu w czystości
- Pokrycie kosztów szkód powstałych z Twojej winy

### 3. Kaucja zabezpieczająca

Kaucja to często spotykane zabezpieczenie wynajmującego. Musisz wiedzieć, że:
- Wysokość kaucji nie jest ograniczona prawnie (zwykle 1-3 miesięczne czynsze)
- Wynajmujący **musi** zwrócić kaucję w terminie określonym w umowie
- Może potrącić z kaucji koszty napraw szkód powstałych z Twojej winy
- **Nie może** zatrzymać kaucji za normalne zużycie mieszkania

## Rozwiązanie umowy najmu

### Kiedy możesz wypowiedzieć umowę?

Sposób wypowiedzenia umowy zalezy od jej rodzaju:

**Najem na czas określony:**
- Zasadniczo nie możesz wypowiedzieć umowy przed upływem terminu
- **Wyjątek**: jeśli umowa zawiera klauzulę o możliwości wcześniejszego wypowiedzenia

**Najem na czas nieokreślony:**
- Możesz wypowiedzieć umowę w każdym czasie
- Okres wypowiedzenia (jeśli nie ustalono inaczej):
  - 3 miesiące - gdy czynsz płacony jest miesięcznie
  - 1 tydzień - gdy czynsz płacony jest tygodniowo
  - 3 dni - gdy czynsz płacony jest dziennie

**Forma wypowiedzenia**: Wypowiedzenie umowy najmu wymaga zachowania **formy pisemnej** pod rygorem nieważności.

### Nadzwyczajne rozwiązanie umowy

W szczególnych przypadkach możesz rozwiązać umowę **bez zachowania okresu wypowiedzenia**:
- Lokal nie nadaje się do zamieszkania (np. grzyb, wilgoć)
- Wynajmujący nie dokonuje niezbędnych napraw
- Wynajmujący narusza Twoje prawa (np. nękanie, wchodzenie bez zgody)

## Zalanie mieszkania - kto ponosi koszty?

Zalanie to jedna z najczęstszych awarii w wynajmowanym mieszkaniu. Odpowiedzialność zależy od przyczyny:

**Ty ponosisz koszty**, jeśli:
- Zalanie powstało z Twojej winy (np. zapomniałeś zakręcić kran)
- Nie dopełniłeś podstawowych obowiązków (np. nie włączyłeś ogrzewania zimą)

**Wynajmujący ponosi koszty**, jeśli:
- Zalanie wynikało z awarii instalacji (stara rura, pęknięcie)
- Zalanie nastąpiło z winy sąsiada

**Ważne**: Zawsze dokumentuj szkodę (zdjęcia, filmy) i niezwłocznie powiadom wynajmującego!

## Podwyżka czynszu

Czy wynajmujący może podnieść czynsz w trakcie umowy?

**Najem na czas określony:**
- Zasadniczo nie, chyba że umowa przewiduje mechanizm waloryzacji
- Klauzula waloryzacyjna musi być precyzyjna (np. "wzrost o inflację wg GUS")

**Najem na czas nieokreślony:**
- Wynajmujący może zgłosić podwyżkę
- Wymaga formy pisemnej
- Jeśli nie zgadzasz się na podwyżkę, możesz wypowiedzieć umowę

## Kiedy warto skonsultować się z prawnikiem?

Choć wiele spraw najmu możesz załatwić samodzielnie, w niektórych sytuacjach warto skonsultować się z prawnikiem:
- Spór o zwrot kaucji
- Eksmisja
- Ustalenie odpowiedzialności za większe szkody
- Sporządzenie lub weryfikacja umowy najmu

## Podsumowanie - Kluczowe punkty

1. **Zawieraj umowę na piśmie** - unikniesz sporów
2. **Dokumentuj stan mieszkania** przy wprowadzeniu i wyprowadzeniu
3. **Zgłaszaj usterki pisemnie** - miej dowód komunikacji
4. **Znaj swoje prawa** - nie bój się ich dochodzić
5. **Wypowiedzenie wymaga formy pisemnej** - pamiętaj o tym

Pamiętaj, że prawo najmu chroni zarówno wynajmującego, jak i najemcę. Znajomość swoich praw to klucz do komfortowego i bezpiecznego najmu mieszkania.

## Źródła prawne

- Ustawa z dnia 23 kwietnia 1964 r. - Kodeks cywilny (Dz.U. 1964 nr 16 poz. 93)
- Ustawa z dnia 21 czerwca 2001 r. o ochronie praw lokatorów (Dz.U. 2001 nr 71 poz. 733)

---

*Artykuł ma charakter informacyjny. W sprawach szczegółowych zalecamy konsultację z prawnikiem specjalizującym się w prawie cywilnym.*
"""

            post = Post(
                agent_id=agent.id,
                title="Prawo Najmu w Polsce - Kompletny Przewodnik 2024",
                slug="prawo-najmu-w-polsce-kompletny-przewodnik-2024",
                content=post_content,
                meta_title="Prawo Najmu 2024: Kompletny Przewodnik dla Najemców | Legitio",
                meta_description="Wszystko o prawach najemcy w Polsce: umowy, kaucje, rozwiązanie kontraktu, zalania mieszkań. Praktyczny przewodnik z przykładami i podstawami prawnymi.",
                excerpt="Wynajem mieszkania to częsta forma korzystania z nieruchomości w Polsce. Poznaj swoje prawa jako najemca - umowy, kaucje, wypowiedzenia i więcej.",
                keywords=["prawo najmu", "najem mieszkania", "umowa najmu", "prawa najemcy", "kaucja", "wypowiedzenie najmu"],
                status="published",
                published_at=datetime.utcnow(),
                word_count=850,
                readability_score=65.0,
                tokens_used=2500
            )
            db.add(post)
            await db.commit()
            await db.refresh(post)
            print(f"✅ Demo post created and published!")
            print(f"   Title: {post.title}")
            print(f"   Slug: {post.slug}")
            print(f"   Status: {post.status}")
            print(f"   URL: http://localhost:5174/blog/{post.slug}")
        else:
            print(f"✅ Demo post already exists: {post.title}")
            print(f"   Status: {post.status}")
            print(f"   URL: http://localhost:5174/blog/{post.slug}")

        print()
        print("🎉 Demo content ready!")
        print(f"   Agent ID: {agent.id}")
        print(f"   Post ID: {post.id}")
        print()
        print("📍 Check it out:")
        print(f"   Dashboard: http://localhost:3000")
        print(f"   Blog page: http://localhost:5174/blog")
        print(f"   Article: http://localhost:5174/blog/{post.slug}")


if __name__ == "__main__":
    asyncio.run(create_demo_content())
