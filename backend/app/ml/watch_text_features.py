"""Текстовые признаки описания/заголовка объявления умных часов.

Данные (не код) — таблицы регулярок. Ничего отсюда трогать не нужно, чтобы просто
подключить модель к парсеру; редактировать имеет смысл только при переобучении,
если аудит находит новый паттерн реплик/б-у-формул, который модель не ловит.

Общие семейства (торг/обмен/рассрочка/цена-по-схеме, реплика/серый импорт/рефаб и т.п.)
+ маркеры, специфичные для часов (реплики Apple Watch, аксессуары, бандлы).
"""
from __future__ import annotations

import re

import pandas as pd


def _c(*patterns: str) -> tuple[re.Pattern, ...]:
    return tuple(re.compile(p, re.I | re.S) for p in patterns)


RULE_FAMILIES = {
    "torg": dict(
        include=_c(r"\bторг\b", r"\bцена\s+обсужда", r"\bваш[иы]\s+цен", r"\bпредлагай[а-я]*\s+цен"),
        exclude=_c(r"\bбез\s+торга?\b", r"\bнет\s+торга\b", r"\bторга\s+нет\b", r"\bторг\s+отсутствует\b",
                   r"\bторг\s+не\s+"),
    ),
    "trade_in": dict(
        include=_c(r"\bобмен\b", r"\btrade[- ]?in\b", r"\bтрейд[- ]?ин\b", r"\bтрейдин\b"),
        exclude=_c(r"\bбез\s+обмена\b", r"\bобмена\s+нет\b", r"\bобмен\s+не\s+", r"\bбез\s+trade[- ]?in\b",
                   r"\bбез\s+трейд[- ]?ин\b"),
    ),
    "installment": dict(
        include=_c(r"\bрассроч", r"\bпо\s+частям\b", r"\bоплата\s+частями\b", r"\bперв[а-я]+\s+взнос\b", r"\bкредит\b"),
        exclude=_c(r"\bбез\s+рассроч", r"\bрассроч[а-я]*\s+нет\b", r"\bрассроч[а-я]*\s+не\s+", r"\bбез\s+кредита\b"),
    ),
    "price_scheme": dict(
        include=_c(r"\bцен[аы].{0,40}\bс\s+уч[её]том\b", r"\bцен[аы].{0,40}\bпри\s+обмен",
                   r"\bцен[аы].{0,40}\bпри\s+trade[- ]?in\b", r"\bцен[аы].{0,40}\bпри\s+трейд",
                   r"\bцен[аы].{0,40}\bпри\s+рассроч", r"\bцен[аы].{0,40}\bв\s+рассроч",
                   r"\bцен[аы].{0,40}\bпри\s+кредит"),
        exclude=_c(r"\bбез\s+торга\b", r"\bбез\s+обмена\b", r"\bбез\s+рассроч", r"\bбез\s+trade[- ]?in\b"),
    ),
}

EXTRA_MARKERS = {
    "replica_word": _c(r"\bреплик", r"\bкопи[яию]\b", r"\b1\s*[:кk]\s*1\b", r"\bлюкс\b", r"\blux\b",
                       r"\bпод\s+оригинал", r"\bне\s+оригинал", r"\bкачество\s+(люкс|премиум|отличное)\b",
                       r"\bкорейск", r"\bтайван", r"\bточная\s+копия"),
    "gray_import": _c(r"\bевротест\b", r"\bбез\s+ростест", r"\bне\s+ростест"),
    "refurb": _c(r"\bвосстановлен", r"\bрефаб", r"\brefurb", r"\bкак\s+новый\b", r"\bсн[яа]т\s+с\s+витрины\b",
                 r"\bвитринн"),
    "used_hint": _c(r"\bб[/\\]?у\b", r"\bпользовались\b", r"\bсостояние\s+(идеал|отличн|хорош)"),
    "official": _c(r"\bростест\b", r"\bофициальн", r"\bгарантия\s+(производителя|1\s*год|12\s*мес)",
                   r"\bчек\b", r"\bкассовый\b", r"\bзапечатан", r"\bне\s+вскрыт", r"\bновый\s+запечатанный\b"),
    "shop_speak": _c(r"\bнаш\s+магазин\b", r"\bв\s+наличии\b", r"\bдоставка\s+по\b", r"\bсамовывоз\b",
                     r"\bвыда[её]м\s+чек\b", r"\bмы\s+находимся\b", r"\bторгов[а-я]+\s+центр"),
    "urgency": _c(r"\bсрочно\b", r"\bсегодня\s+отда[мь]\b", r"\bтолько\s+сегодня\b", r"\bакция\b", r"\bуспей"),
    "verify_offer": _c(r"\bпровер(ка|ить|яйте)\b", r"\bлюбые\s+проверки\b", r"\bпри\s+встрече\s+провер"),
    "contact_bait": _c(r"\bпишите\b.{0,30}(лс|whats|вотс|телег)", r"\bномер\s+в\s+описании\b", r"\bзвоните\b"),
    "no_warranty_hint": _c(r"\bбез\s+гарант", r"\bгарантии\s+нет\b"),
    "used_formula": _c(r"состояние\s+(идеальн|отличн|хорош|нового)", r"как\s+нов(ый|ое)\b",
                       r"в\s+(идеальн|отличн|хорош)[а-я]*\s+состоянии", r"состояни[ея]\s+как\s+у?\s?нов",
                       r"все\s+функции\s+работают", r"полный\s+рабочий\s+функционал",
                       r"отвязан\s+от\s+(всех\s+)?аккаунт", r"без\s+следов\s+использован",
                       r"в\s+пользовании\s+не\s+был", r"не\s+использовался",
                       r"пользовал[ иа]", r"б[/\\]?у\s+\d+\s+дн", r"уценк", r"выставочн[а-я]+\s+образ",
                       r"обменк", r"после\s+(видео\s*)?обзора", r"наклеен[оа]?\s+(защитное\s+)?стекл",
                       r"аккумулятор\s+родной", r"заряд\s+держит",
                       r"для\s+обзор[а]", r"царапин\s+нет", r"без\s+царапин", r"емкость\s+батареи\s+100"),
    "battery_cycles": _c(r"акб\s*100\s*%", r"аккумулятор\s*100\s*%", r"0\s*циклов", r"цикл[ыа]?\s+заряд"),
    "vitrina": _c(r"витрин"),
    "bait_formula": _c(r"цен[аы]\s+(реальн[а-я]*\s+)?(за\s+версию\s+)?в\s+рассрочку",
                       r"акционн[а-я]+\s+(стоимость|цен)", r"промо\s*код", r"промокод",
                       r"узнать\s+подробности\s+акции", r"цен[аы]\s+при\s+покупке\s+в\s+рассрочку",
                       r"цен[аы]\s+ниже\s+рыночной", r"глц"),
    "prepay": _c(r"предоплат[аеу]\s*100", r"по\s+предоплате", r"100\s*%\s+оплат", r"опт\s+от\s+\d"),
    "preorder": _c(r"под\s+заказ", r"привожу\s+на\s+заказ", r"срок\s+поставки", r"предзаказ",
                   r"доступен\s+к\s+заказу"),
    "as_is": _c(r"\bas\s*[- ]?\s*is\b", r"\bас\s+ис\b", r"как\s+есть\b.{0,30}замен"),
    "demo_unit": _c(r"\bldu\b", r"\bдемо\b", r"demo\s+версия", r"демонстрационн"),
}

# специфика часов: реплики Apple Watch, аксессуары, бандлы — собрано аудитом реальных объявлений
WATCH_MARKERS = {
    "wm_replica_apple": _c(
        r"яблок[оа][^.]{0,30}включени",
        r"логотип[^.]{0,30}включени",
        r"отобража[а-яе]+ся\s+как\s+apple\s*watch",
        r"в\s+настройках\s+бл[юу]туса",
        r"(только\s+)?на\s+наших\s+версиях",
        r"исключительно\s+эта\s+верси",
        r"оригинальн[а-я]+\s+интерфейс",
        r"меню\s+как\s+на\s+оригинал",
        r"как\s+у\s+оригинал",
    ),
    "wm_verify_claim": _c(
        r"пробива[а-яе]+ся\s+на\s+(оф|сайте)",
        r"увеличенная\s+гарантия\s+на\s+часы",
        r"провер(ка|ить|яйте)\s+по\s+серийному",
    ),
    "wm_replica_app": _c(
        r"\buufit\b", r"\bwearfit\b", r"\bhiwatch\b", r"\bhry\s*fine\b", r"\bda\s*fit\b",
        r"\bfit\s*pro\b", r"\bfitcloud\b", r"\bwatch\s*assistant\b", r"\bkeep\s*health\b",
        r"без\s+единой\s+рк\b",
    ),
    "wm_replica_model": _c(
        r"\bhk\s?(8|9|10|11)\b", r"\bdt\s?no\.?\s?1\b", r"\bw&o\b", r"\bgs\s?(8|9)\b",
        r"\bx9\s?(pro|max|ultra)?\b", r"\bs9\s+ultra\b", r"\bw59\b", r"\bt900\b",
        r"\bsmart\s+watch\s+(8|9|10|11|x)\b", r"смарт[- ]?часы\s+(8|9|10|11)\s+серии",
        r"(8|9|10|11)[- ]?я?\s+серия\b", r"\bpremium\s+(версия|качество)\b",
        r"люкс[- ]?копия", r"точная\s+копия",
    ),
    "wm_android_compat": _c(
        r"совместим[а-я]*\s+с\s+iphone\s+и\s+android",
        r"(для|поддержка)\s+(ios\s+и\s+android|android\s+и\s+ios)",
        r"работа[ею]т\s+с\s+android",
        r"сопряга[юе]тся\s+через\s+приложение",
    ),
    "wm_accessory": _c(
        r"\bремеш[ок]к", r"\bбраслет\s+для\b", r"\bзарядн[а-я]+\s+(устройств|кабель|док)",
        r"\bзарядка\s+для\b", r"\bчехол\b", r"\bзащитн[а-я]+\s+(стекл|пл[её]нк)",
        r"только\s+(ремешок|браслет|коробка|зарядка)", r"коробка\s+от\b",
        r"\bстекл[оа]\s+для\b", r"\bбез\s+часов\b", r"\bдок[- ]?станци",
        r"миланск[а-я]+\s+плетени[ея]\s+в\s+подарок",
    ),
    "wm_original_claim": _c(
        r"не\s+(реплика|копия|подделка)", r"100\s*%\s+оригинал", r"\bоригинал\b",
        r"серийный\s+номер", r"проверка\s+по\s+серийному",
    ),
    "wm_replica_funcs": _c(
        r"шагомер", r"измерение\s+пульса", r"тонометр", r"давлени[ея]\b",
        r"уровень\s+кислорода", r"мониторинг\s+сна", r"выбор\s+(различных\s+)?циферблат",
        r"водонепроницаемост", r"bluetooth\s+5\.[0-9]", r"врем[яе]\s+работы\s+до\s+\d+\s+час",
    ),
    "wm_bundle": _c(
        r"(в\s+подарок|\+)\s*(airpods|наушники|pods)", r"\b2\s*в\s*1\b", r"\bкомбо\b",
        r"наушники\s+в\s+(комплекте|подарок)",
    ),
}


def norm_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower().replace("ё", "е"))


def rule_family_hits(text: str) -> dict[str, int]:
    out = {}
    for name, fam in RULE_FAMILIES.items():
        hit = any(rx.search(text) for rx in fam["include"]) and not any(rx.search(text) for rx in fam["exclude"])
        out[f"rule_{name}"] = int(hit)
    return out


def extra_marker_hits(text: str) -> dict[str, int]:
    return {f"mark_{name}": int(any(rx.search(text) for rx in rxs)) for name, rxs in EXTRA_MARKERS.items()}


def watch_marker_hits(text: str) -> dict[str, int]:
    return {name: int(any(rx.search(text) for rx in rxs)) for name, rxs in WATCH_MARKERS.items()}


_CYR = set("абвгдежзийклмнопрстуфхцчшщъыьэюя")
_LAT = set("abcdefghijklmnopqrstuvwxyz")


def mixed_script_share(text: str) -> float:
    """Доля слов со смешанной кириллицей/латиницей («ноbый», «запeчаtанный») —
    обфускация против модерации, маркер серых сеток-перекупов."""
    words = re.findall(r"[а-яa-zё]{3,}", text)
    if not words:
        return 0.0
    mixed = sum(1 for w in words if (set(w) & _CYR) and (set(w) & _LAT))
    return mixed / len(words)


def text_stats(text: str) -> dict[str, float]:
    words = text.split()
    digits = sum(1 for ch in text if ch.isdigit())
    emoji_ish = len(re.findall(r"[☀-➿\U0001f000-\U0001faff]", text))
    latin = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    return dict(
        desc_len=len(text),
        desc_words=len(words),
        desc_digit_share=digits / max(len(text), 1),
        desc_latin_share=latin / max(len(text), 1),
        desc_emoji=emoji_ish,
        desc_mixed_script=mixed_script_share(text),
    )


def extract_all_watch(raw_title: object, raw_description: object) -> dict[str, float]:
    """Признаки по title+description — у часов заголовок так же информативен, как текст."""
    title = norm_text(raw_title)
    desc = norm_text(raw_description)
    both = f"{title} {desc}".strip()
    out: dict[str, float] = {}
    out.update(rule_family_hits(both))
    out.update(extra_marker_hits(both))
    out.update(watch_marker_hits(both))
    out.update(text_stats(desc))
    out["title_len"] = len(title)
    out["title_mixed_script"] = mixed_script_share(title)
    return out
