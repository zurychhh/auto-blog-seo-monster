"""
Script to add/update Legitio blog articles from articles.ts data.
"""
import asyncio
from datetime import datetime
from uuid import UUID
from sqlalchemy import select

import sys
sys.path.insert(0, '/Users/user/projects/legitio-landing/blog-backend/backend')

from app.database import AsyncSessionLocal
from app.models.post import Post
from app.models.agent import Agent

# Articles from src/lib/data/articles.ts
ARTICLES = [
    {
        "slug": "prawo-najmu-w-polsce-przewodnik-2025",
        "title": "Prawo Najmu w Polsce - Kompletny Przewodnik 2025",
        "meta_title": "Prawo Najmu w Polsce 2025 - Przewodnik dla Najemców i Wynajmujących",
        "meta_description": "Wszystko o prawach najemcy i wynajmującego w Polsce: umowy najmu, kaucje, wypowiedzenie, najem okazjonalny. Aktualny przewodnik na 2025 rok.",
        "excerpt": "Kompleksowy przewodnik po prawie najmu w Polsce - poznaj swoje prawa jako najemca lub wynajmujący.",
        "focus_keyword": "prawo najmu",
        "published_at": "2025-01-15",
        "content": """
<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-balance-scale"></i> Podstawa prawna</div>
<p><strong>Kodeks cywilny</strong> (art. 659-692) oraz <strong>Ustawa o ochronie praw lokatorów</strong> z 21 czerwca 2001 r.</p>
</div>

<h2>Podstawy prawne najmu w Polsce</h2>

<p>Wynajem mieszkania w Polsce regulowany jest przez kilka aktów prawnych. Ustawa o ochronie praw lokatorów chroni najemców będących <strong>osobami fizycznymi</strong>, którzy korzystają z lokalu dla zaspokajania potrzeb mieszkaniowych.</p>

<p>Jeśli najemcą jest firma lub lokal służy do działalności gospodarczej, zastosowanie mają wyłącznie przepisy Kodeksu cywilnego.</p>

<hr class="section-divider" />

<h2>Rodzaje umów najmu</h2>

<div class="card-grid">
<div class="info-card">
<h3><i class="fas fa-file-contract"></i> Zwykła umowa najmu</h3>
<p>Może być zawarta na czas określony lub nieokreślony. Najemca jest chroniony przepisami ustawy o ochronie praw lokatorów.</p>
</div>

<div class="info-card">
<h3><i class="fas fa-home"></i> Najem okazjonalny</h3>
<p>Dla właścicieli nieprowadzących działalności w zakresie wynajmu. Maksymalnie na <strong>10 lat</strong>.</p>
</div>

<div class="info-card">
<h3><i class="fas fa-building"></i> Najem instytucjonalny</h3>
<p>Dla podmiotów prowadzących działalność gospodarczą w zakresie wynajmu. Bez limitu czasowego.</p>
</div>
</div>

<h3>Najem okazjonalny - szczegóły</h3>

<ul>
<li>Zawierana na czas oznaczony, <strong>maksymalnie 10 lat</strong></li>
<li>Wymaga oświadczenia najemcy w formie aktu notarialnego o poddaniu się egzekucji</li>
<li>Najemca musi wskazać lokal, do którego się wyprowadzi</li>
<li>Właściciel musi zgłosić umowę do US w ciągu <strong>14 dni</strong></li>
<li>Kaucja: maksymalnie <strong>6-krotność czynszu</strong></li>
</ul>

<hr class="section-divider" />

<h2>Kaucja - zasady</h2>

<div class="highlight-box">
<div class="highlight-grid">
<div class="highlight-item">
<span class="highlight-label">Najem okazjonalny</span>
<span class="highlight-value">max. 6x czynsz</span>
</div>
<div class="highlight-item">
<span class="highlight-label">Zwykły najem</span>
<span class="highlight-value">zwyczajowo 1-3x czynsz</span>
</div>
<div class="highlight-item">
<span class="highlight-label">Termin zwrotu</span>
<span class="highlight-value">1 miesiąc od opróżnienia</span>
</div>
</div>
</div>

<p>Właściciel może potrącić z kaucji zaległości czynszowe i koszty napraw szkód wykraczających poza normalne zużycie.</p>

<hr class="section-divider" />

<h2>Prawa i obowiązki najemcy</h2>

<div class="two-columns">
<div class="column">
<h4 class="column-title green"><i class="fas fa-check-circle"></i> Najemca MA PRAWO do:</h4>
<ul>
<li>Korzystania z lokalu zgodnie z przeznaczeniem</li>
<li>Żądania usunięcia wad lokalu</li>
<li>Obniżenia czynszu za czas trwania wad</li>
<li>Wypowiedzenia umowy przy wadach zagrażających zdrowiu</li>
</ul>
</div>

<div class="column">
<h4 class="column-title orange"><i class="fas fa-exclamation-circle"></i> Najemca MUSI:</h4>
<ul>
<li>Terminowo płacić czynsz i opłaty</li>
<li>Używać lokalu zgodnie z umową</li>
<li>Dbać o lokal</li>
<li>Przestrzegać porządku domowego</li>
</ul>
</div>
</div>

<hr class="section-divider" />

<h2>Wypowiedzenie umowy najmu</h2>

<h3>Przez wynajmującego</h3>

<div class="info-box yellow">
<div class="info-box-title"><i class="fas fa-exclamation-triangle"></i> Ważne</div>
<p>Wypowiedzenie przez właściciela jest <strong>ściśle regulowane ustawą</strong>. Nie można wypowiedzieć umowy bez uzasadnionej przyczyny!</p>
</div>

<p><strong>Możliwe przyczyny wypowiedzenia:</strong></p>
<ul>
<li>Zaleganie z czynszem przez <strong>min. 3 pełne okresy płatności</strong> (po wezwaniu do zapłaty)</li>
<li>Podnajęcie lokalu bez zgody właściciela</li>
<li>Używanie lokalu niezgodnie z przeznaczeniem</li>
<li>Zamiar zamieszkania właściciela (wypowiedzenie z <strong>3-letnim</strong> wyprzedzeniem!)</li>
<li>Konieczność rozbiórki lub remontu budynku</li>
</ul>

<h3>Przez najemcę</h3>

<ul>
<li><strong>Umowa na czas nieokreślony:</strong> 3-miesięczny okres wypowiedzenia (przy czynszu miesięcznym)</li>
<li><strong>Umowa na czas określony:</strong> tylko jeśli umowa to przewiduje lub za porozumieniem stron</li>
<li><strong>Natychmiastowe:</strong> gdy lokal ma wady zagrażające zdrowiu</li>
</ul>

<hr class="section-divider" />

<h2>Zmiany od 2025 roku</h2>

<div class="info-box green">
<div class="info-box-title"><i class="fas fa-calendar-alt"></i> Nowości 2025</div>
<ul style="margin: 0;">
<li><strong>Lokal zastępczy:</strong> właściciel (nie gmina) musi go zapewnić przy wypowiedzeniu z powodu rozbiórki/remontu</li>
<li><strong>Limit podwyżek:</strong> nie mogą przekroczyć wskaźnika inflacji z poprzedniego roku</li>
<li><strong>Najem senioralny:</strong> nowa instytucja dla osób starszych</li>
</ul>
</div>

<hr class="section-divider" />

<h2>Praktyczne wskazówki</h2>

<div class="tips-list">
<div class="tip-item">
<span class="tip-number">1</span>
<div class="tip-content">
<strong>Zawsze zawieraj umowę na piśmie</strong>
<p>Ustna umowa najmu jest ważna, ale trudna do udowodnienia w razie sporu.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">2</span>
<div class="tip-content">
<strong>Sporządź protokół zdawczo-odbiorczy</strong>
<p>Ze zdjęciami i szczegółowym opisem stanu lokalu - chroni obie strony.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">3</span>
<div class="tip-content">
<strong>Zachowuj dowody wpłat</strong>
<p>Potwierdzenia przelewów, pokwitowania - mogą być kluczowe przy sporach.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">4</span>
<div class="tip-content">
<strong>Sprawdź księgę wieczystą</strong>
<p>Upewnij się, że wynajmujący jest faktycznym właścicielem nieruchomości.</p>
</div>
</div>
</div>

<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji. W sprawach indywidualnych zalecamy konsultację z profesjonalnym prawnikiem.</p>
</div>
"""
    },
    {
        "slug": "urlop-wypoczynkowy-przewodnik",
        "title": "Urlop Wypoczynkowy - Wszystko Co Musisz Wiedzieć",
        "meta_title": "Urlop Wypoczynkowy 2025 - Ile Dni Przysługuje? Kodeks Pracy",
        "meta_description": "Kompletny przewodnik po urlopie wypoczynkowym w Polsce: wymiar urlopu, zasady udzielania, urlop zaległy, nowe przepisy 2025. Sprawdź swoje prawa.",
        "excerpt": "Ile dni urlopu Ci przysługuje? Poznaj zasady urlopu wypoczynkowego według Kodeksu pracy.",
        "focus_keyword": "prawo pracy",
        "published_at": "2025-01-10",
        "content": """
<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-balance-scale"></i> Podstawa prawna</div>
<p><strong>Kodeks pracy</strong> - art. 152-173, w szczególności art. 154 dotyczący wymiaru urlopu.</p>
</div>

<h2>Podstawowy wymiar urlopu</h2>

<div class="highlight-box large">
<div class="highlight-grid two">
<div class="highlight-item big">
<span class="highlight-value large">20 dni</span>
<span class="highlight-label">staż pracy poniżej 10 lat</span>
</div>
<div class="highlight-item big">
<span class="highlight-value large">26 dni</span>
<span class="highlight-label">staż pracy 10 lat i więcej</span>
</div>
</div>
</div>

<p>Powyższy wymiar dotyczy osób zatrudnionych na <strong>pełen etat</strong>. Przy niepełnym etacie urlop oblicza się proporcjonalnie (np. przy 1/2 etatu: 10 lub 13 dni).</p>

<hr class="section-divider" />

<h2>Co wlicza się do stażu pracy?</h2>

<p>Do okresu zatrudnienia, od którego zależy wymiar urlopu, wlicza się:</p>

<ul>
<li><strong>Wszystkie poprzednie okresy zatrudnienia</strong> (bez względu na przerwy)</li>
<li><strong>Okres nauki</strong> - według ukończonej szkoły</li>
</ul>

<div class="info-card standalone">
<h4><i class="fas fa-graduation-cap"></i> Okresy nauki doliczane do stażu</h4>
<div class="data-grid">
<div class="data-item"><span class="data-label">Zasadnicza szkoła zawodowa</span><span class="data-value">3 lata</span></div>
<div class="data-item"><span class="data-label">Średnia szkoła zawodowa</span><span class="data-value">5 lat</span></div>
<div class="data-item"><span class="data-label">Średnia szkoła ogólnokształcąca</span><span class="data-value">4 lata</span></div>
<div class="data-item"><span class="data-label">Szkoła policealna</span><span class="data-value">6 lat</span></div>
<div class="data-item"><span class="data-label">Szkoła wyższa (studia)</span><span class="data-value">8 lat</span></div>
</div>
</div>

<div class="info-box yellow">
<div class="info-box-title"><i class="fas fa-lightbulb"></i> Pamiętaj</div>
<p>Okresy nauki <strong>nie sumują się</strong> - zalicza się tylko jeden, najkorzystniejszy dla pracownika.</p>
</div>

<hr class="section-divider" />

<h2>Nawet 35 dni wolnego rocznie!</h2>

<p>Od kwietnia 2023 roku, dzięki wdrożeniu unijnej dyrektywy <strong>work-life balance</strong>, pracownicy mogą korzystać z dodatkowych dni wolnych:</p>

<div class="card-grid">
<div class="info-card">
<h3><i class="fas fa-heart"></i> Urlop opiekuńczy</h3>
<div class="card-highlight">5 dni</div>
<p>Na opiekę nad członkiem rodziny lub osobą zamieszkującą wspólnie.</p>
<span class="card-note warning">Bezpłatny</span>
</div>

<div class="info-card">
<h3><i class="fas fa-bolt"></i> Siła wyższa</h3>
<div class="card-highlight">2 dni / 16h</div>
<p>W pilnych sprawach rodzinnych (choroba, wypadek).</p>
<span class="card-note">50% wynagrodzenia</span>
</div>

<div class="info-card">
<h3><i class="fas fa-child"></i> Opieka nad dzieckiem</h3>
<div class="card-highlight">2 dni / 16h</div>
<p>Dla rodzica dziecka do 14 roku życia.</p>
<span class="card-note success">Pełne wynagrodzenie</span>
</div>
</div>

<hr class="section-divider" />

<h2>Zasady udzielania urlopu</h2>

<div class="tips-list">
<div class="tip-item">
<span class="tip-number">1</span>
<div class="tip-content">
<strong>Plan urlopów</strong>
<p>Pracodawca ustala go do końca roku na rok następny, uwzględniając wnioski pracowników.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">2</span>
<div class="tip-content">
<strong>Minimum 14 dni ciągiem</strong>
<p>Co najmniej jedna część urlopu powinna trwać nieprzerwanie 14 dni kalendarzowych.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">3</span>
<div class="tip-content">
<strong>Urlop w naturze</strong>
<p>Pracodawca nie może zastąpić urlopu ekwiwalentem pieniężnym (poza rozwiązaniem umowy).</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">4</span>
<div class="tip-content">
<strong>Zgoda pracodawcy</strong>
<p>Na urlop poza planem potrzebna jest zgoda pracodawcy.</p>
</div>
</div>
</div>

<hr class="section-divider" />

<h2>Urlop zaległy</h2>

<div class="info-box orange">
<div class="info-box-title"><i class="fas fa-calendar-times"></i> Termin wykorzystania</div>
<p>Niewykorzystany urlop przechodzi na rok następny. Pracodawca <strong>musi</strong> udzielić go do <strong>30 września</strong> następnego roku.</p>
</div>

<div class="two-columns">
<div class="column">
<h4>Co warto wiedzieć:</h4>
<ul>
<li>Po 30 września prawo do urlopu <strong>nie przepada</strong></li>
<li>Przedawnia się dopiero po <strong>3 latach</strong></li>
<li>Pracodawca może jednostronnie wyznaczyć termin</li>
</ul>
</div>

<div class="column">
<h4>Urlop na żądanie:</h4>
<ul>
<li><strong>4 dni</strong> w roku kalendarzowym</li>
<li>Wlicza się do puli urlopu (nie jest dodatkowy)</li>
<li>Zgłoszenie najpóźniej w dniu rozpoczęcia</li>
</ul>
</div>
</div>

<hr class="section-divider" />

<h2>Urlop a choroba</h2>

<div class="two-columns">
<div class="column">
<div class="info-card standalone small">
<h4><i class="fas fa-thermometer-half"></i> Choroba PRZED urlopem</h4>
<p>Urlop przesuwa się <strong>automatycznie</strong>. Pracodawca nie może odmówić.</p>
</div>
</div>

<div class="column">
<div class="info-card standalone small">
<h4><i class="fas fa-bed"></i> Choroba W TRAKCIE urlopu</h4>
<p>Urlop się <strong>przerywa</strong>. Niewykorzystaną część można wykorzystać później.</p>
</div>
</div>
</div>

<hr class="section-divider" />

<h2>Pierwszy rok pracy</h2>

<p>W pierwszym roku pracy prawo do urlopu nabywa się <strong>proporcjonalnie</strong>:</p>

<ul>
<li>1/12 przysługującego wymiaru za każdy przepracowany miesiąc</li>
<li>Przy 20-dniowym wymiarze to ok. <strong>1,66 dnia/miesiąc</strong></li>
<li>Niepełne dni zaokrągla się <strong>w górę</strong></li>
</ul>

<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji. W sprawach indywidualnych zalecamy konsultację z profesjonalnym prawnikiem.</p>
</div>
"""
    },
    {
        "slug": "zwrot-towaru-prawa-konsumenta",
        "title": "Zwrot Towaru w Sklepie - Twoje Prawa",
        "meta_title": "Zwrot Towaru 2025 - Prawa Konsumenta, 14 Dni, Reklamacja",
        "meta_description": "Poznaj swoje prawa przy zwrocie towaru: 14 dni na odstąpienie od umowy, reklamacja, gwarancja. Kompletny przewodnik po prawach konsumenta w Polsce.",
        "excerpt": "14 dni na zwrot, reklamacje, gwarancje - poznaj swoje prawa jako konsument w Polsce.",
        "focus_keyword": "konsumenckie",
        "published_at": "2025-01-05",
        "content": """
<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-balance-scale"></i> Podstawa prawna</div>
<p><strong>Ustawa o prawach konsumenta</strong> z 30 maja 2014 r. (implementacja Dyrektywy UE 2011/83).</p>
</div>

<h2>Prawo odstąpienia - zakupy online</h2>

<p>Przy zakupach przez internet konsument ma prawo odstąpić od umowy <strong>bez podania przyczyny</strong>.</p>

<div class="highlight-box large">
<div class="highlight-grid three">
<div class="highlight-item big">
<span class="highlight-value large">14 dni</span>
<span class="highlight-label">zakupy internetowe i telefoniczne</span>
</div>
<div class="highlight-item big">
<span class="highlight-value large">30 dni</span>
<span class="highlight-label">nieumówiona wizyta sprzedawcy</span>
</div>
<div class="highlight-item big">
<span class="highlight-value large">12 mies.</span>
<span class="highlight-label">gdy sprzedawca nie poinformował o prawie</span>
</div>
</div>
</div>

<div class="info-box yellow">
<div class="info-box-title"><i class="fas fa-clock"></i> Kiedy liczymy termin?</div>
<p>Termin 14 dni liczy się <strong>od dnia otrzymania towaru</strong>, nie od daty zamówienia!</p>
</div>

<hr class="section-divider" />

<h2>Jak odstąpić od umowy?</h2>

<div class="tips-list">
<div class="tip-item">
<span class="tip-number">1</span>
<div class="tip-content">
<strong>Złóż oświadczenie o odstąpieniu</strong>
<p>Pisemnie, emailem lub przez formularz sklepu. Wystarczy wysłać przed upływem terminu.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">2</span>
<div class="tip-content">
<strong>Zwróć towar w ciągu 14 dni</strong>
<p>Od momentu złożenia oświadczenia masz 14 dni na odesłanie produktu.</p>
</div>
</div>

<div class="tip-item">
<span class="tip-number">3</span>
<div class="tip-content">
<strong>Otrzymaj zwrot pieniędzy</strong>
<p>Sprzedawca ma 14 dni na zwrot wszystkich płatności, włącznie z kosztem najtańszej dostawy.</p>
</div>
</div>
</div>

<hr class="section-divider" />

<h2>Sklep stacjonarny vs. online</h2>

<div class="comparison-box">
<div class="comparison-item">
<div class="comparison-header negative">
<i class="fas fa-store"></i>
<h4>Sklep stacjonarny</h4>
</div>
<div class="comparison-content">
<p><strong>NIE MA</strong> ustawowego prawa do zwrotu towaru bez wady!</p>
<p class="small">Zwrot możliwy tylko gdy sklep oferuje taką możliwość (polityka sklepu) lub towar ma wadę (reklamacja).</p>
</div>
</div>

<div class="comparison-item">
<div class="comparison-header positive">
<i class="fas fa-laptop"></i>
<h4>Sklep internetowy</h4>
</div>
<div class="comparison-content">
<p><strong>14 DNI</strong> na zwrot bez podania przyczyny!</p>
<p class="small">Prawo gwarantowane ustawą. Sprzedawca nie może go ograniczyć.</p>
</div>
</div>
</div>

<hr class="section-divider" />

<h2>Stan zwracanego towaru</h2>

<div class="two-columns">
<div class="column">
<h4 class="column-title green"><i class="fas fa-check"></i> Możesz:</h4>
<ul>
<li>Rozpakować i obejrzeć produkt</li>
<li>Przymierzyć ubrania</li>
<li>Sprawdzić działanie urządzenia</li>
</ul>
</div>

<div class="column">
<h4 class="column-title red"><i class="fas fa-times"></i> Uważaj:</h4>
<ul>
<li>Używanie ponad miarę = zmniejszenie wartości</li>
<li>Sprzedawca może potrącić różnicę</li>
<li>Oryginalne opakowanie <strong>nie jest wymagane</strong></li>
</ul>
</div>
</div>

<hr class="section-divider" />

<h2>Towary wyłączone z prawa zwrotu</h2>

<div class="info-box orange">
<div class="info-box-title"><i class="fas fa-ban"></i> Nie podlegają zwrotowi:</div>
<ul style="margin: 0;">
<li>Towary wykonane na zamówienie, personalizowane</li>
<li>Produkty szybko psujące się</li>
<li>Towary w zapieczętowanym opakowaniu (po otwarciu) - ze względów higienicznych</li>
<li>Nagrania audio/video i programy po otwarciu</li>
<li>Prasa (gazety, czasopisma)</li>
<li>Treści cyfrowe po rozpoczęciu świadczenia</li>
</ul>
</div>

<hr class="section-divider" />

<h2>Reklamacja - niezgodność z umową</h2>

<p>Jeśli towar ma wadę, przysługuje Ci prawo do <strong>reklamacji</strong>:</p>

<div class="highlight-box">
<div class="highlight-grid two">
<div class="highlight-item">
<span class="highlight-label">Odpowiedzialność sprzedawcy</span>
<span class="highlight-value">2 lata</span>
</div>
<div class="highlight-item">
<span class="highlight-label">Domniemanie wady od początku</span>
<span class="highlight-value">1 rok</span>
</div>
</div>
</div>

<h3>Czego możesz żądać?</h3>

<div class="steps-box">
<div class="step">
<div class="step-header">
<span class="step-number">Krok 1</span>
<span class="step-title">W pierwszej kolejności</span>
</div>
<div class="step-options">
<span class="step-option"><i class="fas fa-wrench"></i> Naprawa towaru</span>
<span class="step-or">lub</span>
<span class="step-option"><i class="fas fa-exchange-alt"></i> Wymiana na nowy</span>
</div>
</div>

<div class="step">
<div class="step-header">
<span class="step-number">Krok 2</span>
<span class="step-title">Jeśli naprawa/wymiana niemożliwa</span>
</div>
<div class="step-options">
<span class="step-option"><i class="fas fa-percentage"></i> Obniżenie ceny</span>
<span class="step-or">lub</span>
<span class="step-option"><i class="fas fa-undo"></i> Odstąpienie od umowy</span>
</div>
</div>
</div>

<div class="info-box green">
<div class="info-box-title"><i class="fas fa-clock"></i> Termin odpowiedzi</div>
<p>Sprzedawca ma <strong>14 dni</strong> na ustosunkowanie się do reklamacji. Brak odpowiedzi = uznanie reklamacji!</p>
</div>

<hr class="section-divider" />

<h2>Reklamacja vs. Gwarancja</h2>

<div class="table-container">
<table class="comparison-table">
<thead>
<tr>
<th></th>
<th>Reklamacja (rękojmia)</th>
<th>Gwarancja</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Podstawa</strong></td>
<td>Z mocy prawa</td>
<td>Dobrowolna</td>
</tr>
<tr>
<td><strong>Do kogo?</strong></td>
<td>Do sprzedawcy</td>
<td>Do gwaranta (producenta)</td>
</tr>
<tr>
<td><strong>Okres</strong></td>
<td>2 lata od zakupu</td>
<td>Określony przez gwaranta</td>
</tr>
<tr>
<td><strong>Zakres</strong></td>
<td>Określony ustawą</td>
<td>Określony przez gwaranta</td>
</tr>
</tbody>
</table>
</div>

<div class="info-box blue">
<div class="info-box-title"><i class="fas fa-lightbulb"></i> Wskazówka</div>
<p>Konsument <strong>sam wybiera</strong>, czy składa reklamację z tytułu rękojmi (do sprzedawcy) czy gwarancji (do producenta). Wybierz korzystniejszą opcję!</p>
</div>

<hr class="section-divider" />

<h2>Gdzie szukać pomocy?</h2>

<div class="card-grid four">
<div class="info-card small">
<h4><i class="fas fa-user-tie"></i> Rzecznik Konsumentów</h4>
<p>Bezpłatna pomoc w każdym powiecie</p>
</div>

<div class="info-card small">
<h4><i class="fas fa-landmark"></i> UOKiK</h4>
<p>Urząd Ochrony Konkurencji i Konsumentów</p>
</div>

<div class="info-card small">
<h4><i class="fas fa-search"></i> Inspekcja Handlowa</h4>
<p>Kontrola przestrzegania praw</p>
</div>

<div class="info-card small">
<h4><i class="fas fa-globe-europe"></i> ECC</h4>
<p>Europejskie Centrum Konsumenckie (zakupy z UE)</p>
</div>
</div>

<div class="disclaimer-box">
<p><strong>Zastrzeżenie:</strong> Niniejszy artykuł ma charakter wyłącznie informacyjny i edukacyjny. Nie stanowi porady prawnej ani nie zastępuje konsultacji z prawnikiem. Legitio.pl nie ponosi odpowiedzialności za decyzje podjęte na podstawie powyższych informacji. W sprawach indywidualnych zalecamy konsultację z profesjonalnym prawnikiem.</p>
</div>
"""
    }
]


async def main():
    async with AsyncSessionLocal() as db:
        # Get existing agent
        result = await db.execute(select(Agent).limit(1))
        agent = result.scalar_one_or_none()

        if not agent:
            print("ERROR: No agent found. Create one first.")
            return

        print(f"Using agent: {agent.name} (ID: {agent.id})")

        for article in ARTICLES:
            # Check if exists
            existing = await db.execute(
                select(Post).where(Post.slug == article["slug"])
            )
            post = existing.scalar_one_or_none()

            pub_date = datetime.strptime(article["published_at"], "%Y-%m-%d")

            if post:
                # Update existing
                post.title = article["title"]
                post.content = article["content"]
                post.excerpt = article["excerpt"]
                post.meta_title = article["meta_title"]
                post.meta_description = article["meta_description"]
                post.keywords = [article["focus_keyword"]]
                post.status = "published"
                post.published_at = pub_date
                print(f"✅ Updated: {article['slug']}")
            else:
                # Create new
                new_post = Post(
                    agent_id=agent.id,
                    title=article["title"],
                    slug=article["slug"],
                    content=article["content"],
                    excerpt=article["excerpt"],
                    meta_title=article["meta_title"],
                    meta_description=article["meta_description"],
                    keywords=[article["focus_keyword"]],
                    status="published",
                    published_at=pub_date,
                    word_count=len(article["content"].split()),
                    tokens_used=0,
                )
                db.add(new_post)
                print(f"✅ Created: {article['slug']}")

        await db.commit()
        print("\n✅ All articles synced to database!")


if __name__ == "__main__":
    asyncio.run(main())
