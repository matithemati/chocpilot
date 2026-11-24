"""Animowane wygaszacze ekranu LCD – jedno źródło danych dla firmware i aplikacji.

Każda animacja to pixel-art (ramki jako tekst, znak = kolor z palety, „.” = przezroczysty)
przesuwany po ekranie krokami. firmware/tools/gen_savers.py zamienia te dane na
firmware/src/saver_data.h (paleta RGB565, piksele 4 bity), a gui/lcd.py rysuje z nich podgląd –
oba używają tej samej osi czasu (saver_pose), więc podgląd wygląda jak ekran płytki.

Nowa animacja: dopisz Saver do SAVERS i uruchom generator. W przyszłości własne GIF-y będą
zamieniane w aplikacji na ten sam format (≤ 15 kolorów + przezroczystość, ramki w pikselach)
i wysyłane do urządzenia.
"""

from __future__ import annotations

from dataclasses import dataclass

SCREEN_W, SCREEN_H = 320, 240
GROUND_Y = 196  # stopy postaci stoją na tej linii
SKY = (12, 16, 28)
GROUND = (30, 54, 36)
GROUND_LINE = (70, 120, 72)
GROUND_LINE_H = 3
# Zegar HH:MM u góry na środku (czas z aplikacji); krój 5×7 w tej skali (znak 6·skala px).
CLOCK_Y = 18
CLOCK_SCALE = 5
CLOCK_COLOR = (200, 210, 230)

Rgb = tuple[int, int, int]


@dataclass(frozen=True)
class Step:
    frame: int  # numer ramki
    dx: int  # przesunięcie w prawo [px ekranu] w tym kroku
    dy: int  # wysokość nad ziemią [px ekranu]


@dataclass(frozen=True)
class Saver:
    name: str  # identyfikator w protokole (a–z, 0–9, _ – do 11 znaków)
    palette: dict[str, Rgb]  # znak → kolor; „.” = przezroczysty
    frames: tuple[tuple[str, ...], ...]
    steps: tuple[Step, ...]
    frame_ms: int
    scale: int

    @property
    def width(self) -> int:
        return len(self.frames[0][0])

    @property
    def height(self) -> int:
        return len(self.frames[0])

    @property
    def cycle_dx(self) -> int:
        return sum(s.dx for s in self.steps)

    def color_index(self) -> list[str]:
        """Kolejność kolorów w palecie urządzenia: indeks 0 = przezroczysty."""
        return [".", *self.palette]


RABBIT_SIT = (
    "..............kk..kk....",
    ".............kfpkkfpk...",
    ".............kfpkkfpk...",
    ".............kfpkkfpk...",
    "..............kfkkfk....",
    ".............kffffffk...",
    "............kfffffefffk.",
    "....kkkkkkkkffffffffffpk",
    "...kffffffffffffffffffk.",
    "..kwfffffffffffffffffk..",
    ".kwwffffffffffffffffk...",
    "..kwfffffffffffffflk....",
    "...kfffffffffffllllk....",
    "...kffffffkkkkllllkk....",
    "...kfffffffk...kffk.....",
    "...kkkkkkkkk...kkkk.....",
)

RABBIT_LEAP = (
    "........................",
    "........................",
    "...........kkkkkk.......",
    "..........kppppffkk.....",
    "...........kkkkkfffk....",
    "..............kffffefk..",
    "....kkkkkkkkkkffffffffpk",
    "..kkfffffffffffffffffk..",
    ".kwwffffffffffffffffk...",
    "kwwfffffffffffffffllk...",
    ".kkfffffffffffllllk.....",
    "kffkk...........kkfffkk.",
    "kfk...............kfffk.",
    "kk.................kkk..",
    "........................",
    "........................",
)

# Pembroke corgi z boku: duże stojące uszy, biała strzałka i pysk, biała pierś i skarpetki.
CORGI_TROT_A = (
    "...........................k...k........",
    "..........................kok.kok.......",
    "..........................kpokkpok......",
    ".........................kppokppook.....",
    ".........................kppoopppok.....",
    ".........................kpoooopoook....",
    "........................kooooooooook....",
    "........................koooooowonok....",
    "........................koooooowwoookkk.",
    "........................ksooowwwwwwwwwnk",
    "...kkkkkkkkkkkkkkkkkkkkksooowwwwwwwwwkk.",
    "..kssssssssssssssssssssosoowwwwwwwpkk...",
    ".kooooooooooooooooooooooosowwwwwwk......",
    ".koooooooooooooooooooooooowwwwwwk.......",
    "kwoooooooooooooooooooooooowwwwwwk.......",
    "kwwsoooooooooooooooooooooswwwwwk........",
    "kwwwssoooooooooooooooosssswwwwk.........",
    ".kwwwwgggggggggggggggggwwwk.............",
    "..koook.kook..........koook.kook........",
    ".koook...kook........koook....kook......",
    ".kowk.....kwk........kowk......kwk......",
    "kwwk......kwwk......kwwk.......kwwk.....",
    "kkk.......kkkk......kkk........kkkk.....",
    "........................................",
)

CORGI_TROT_B = (
    "...........................k...k........",
    "..........................kok.kok.......",
    "..........................kpokkpok......",
    ".........................kppokppook.....",
    ".........................kppoopppok.....",
    ".........................kpoooopoook....",
    "........................kooooooooook....",
    "........................koooooowonok....",
    "........................koooooowwoookkk.",
    "........................ksooowwwwwwwwwnk",
    "...kkkkkkkkkkkkkkkkkkkkksooowwwwwwwwwkk.",
    "..kssssssssssssssssssssosoowwwwwwwpkk...",
    ".kooooooooooooooooooooooosowwwwwwk......",
    ".koooooooooooooooooooooooowwwwwwk.......",
    "kwoooooooooooooooooooooooowwwwwwk.......",
    "kwwsoooooooooooooooooooooswwwwwk........",
    "kwwwssoooooooooooooooosssswwwwk.........",
    ".kwwwwgggggggggggggggggwwwk.............",
    "...koook.kook.........koook.kook........",
    "....koookkook.........kookkook..........",
    ".....kowkwk...........kowkwk............",
    ".....kwwkwwk..........kwwkwwk...........",
    ".....kkkkkkk..........kkkkkkk...........",
    "........................................",
)

SAVERS: tuple[Saver, ...] = (
    Saver(
        name="rabbit",
        palette={
            "k": (43, 34, 32),
            "f": (180, 135, 90),
            "l": (233, 216, 188),
            "p": (233, 154, 169),
            "e": (13, 13, 13),
            "w": (244, 241, 234),
        },
        frames=(RABBIT_SIT, RABBIT_LEAP),
        # chwila siedzenia, skok łukiem, lądowanie
        steps=(
            Step(0, 0, 0),
            Step(0, 0, 0),
            Step(0, 0, 0),
            Step(1, 8, 20),
            Step(1, 8, 36),
            Step(1, 8, 44),
            Step(1, 8, 36),
            Step(1, 8, 20),
            Step(0, 4, 0),
        ),
        frame_ms=90,
        scale=5,
    ),
    Saver(
        name="corgi",
        palette={
            "k": (42, 24, 16),  # kontur
            "o": (216, 121, 42),  # rude futro
            "s": (169, 90, 30),  # cień futra (grzbiet, zad)
            "w": (247, 240, 227),  # białe: pysk, pierś, brzuch, skarpetki
            "g": (214, 203, 185),  # cień białego
            "n": (18, 16, 16),  # nos i oko
            "p": (232, 138, 150),  # wnętrze uszu, język
        },
        frames=(CORGI_TROT_A, CORGI_TROT_B),
        steps=(Step(0, 6, 0), Step(1, 6, 4)),  # kłus z lekkim podskokiem
        frame_ms=100,
        scale=4,
    ),
)

NAMES: tuple[str, ...] = tuple(s.name for s in SAVERS)


def saver(name: str) -> Saver | None:
    return next((s for s in SAVERS if s.name == name), None)


@dataclass(frozen=True)
class Pose:
    frame: int
    x: int  # lewy górny róg postaci na ekranie (może wychodzić poza ekran)
    y: int


def saver_pose(s: Saver, t_ms: int) -> Pose:
    """Położenie postaci po t_ms od startu wygaszacza (arytmetyka jak firmware/src/saver.cpp).

    Postać wchodzi z lewej (cała poza ekranem) i idzie w prawo; po zejściu z prawej krawędzi
    wraca z lewej.
    """
    n = max(0, t_ms) // s.frame_ms
    cycles, index = divmod(n, len(s.steps))
    pos = cycles * s.cycle_dx + sum(st.dx for st in s.steps[: index + 1])
    w = s.width * s.scale
    step = s.steps[index]
    x = pos % (SCREEN_W + w) - w
    y = GROUND_Y - s.height * s.scale - step.dy
    return Pose(step.frame, x, y)
