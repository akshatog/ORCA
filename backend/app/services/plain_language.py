"""Plain-language advice.

Everything here is written for someone who has never read a marine bulletin.
Rules we hold ourselves to:

  * no jargon — "waves are about as tall as a person", not "Hs 1.8 m"
  * no percentages without a word for them — "good chance", not "62%"
  * clock times, not ISO timestamps — "between 2 PM and 6 PM"
  * every instruction is an action — "come back before dark", not "advisory"
  * the safety line always comes first, before any advice about fish

Supported languages: en, hi, mr, ta, te, bn, ml
The technical numbers still exist everywhere else in the API. This module is
the translation layer, not a replacement for the evidence.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

Language = str

_SUPPORTED = ("en", "hi", "mr", "ta", "te", "bn", "ml")


def _pick(d: Dict[str, str], lang: Language) -> str:
    """Return d[lang] if it exists, else d['en']."""
    return d.get(lang) or d.get("en", "")


def clock(hour: int) -> Dict[Language, str]:
    """12-hour clock in each language — how people actually say the time."""
    h = int(hour) % 24
    h12 = h % 12 or 12
    suffix_en = "AM" if h < 12 else "PM"

    hi_prefix = "सुबह" if 4 <= h < 12 else "दोपहर" if 12 <= h < 17 else "शाम" if 17 <= h < 20 else "रात"
    mr_prefix = "सकाळी" if 4 <= h < 12 else "दुपारी" if 12 <= h < 17 else "संध्याकाळी" if 17 <= h < 20 else "रात्री"
    ta_prefix = "காலை" if 4 <= h < 12 else "மதியம்" if 12 <= h < 17 else "மாலை" if 17 <= h < 20 else "இரவு"
    te_prefix = "ఉదయం" if 4 <= h < 12 else "మధ్యాహ్నం" if 12 <= h < 17 else "సాయంత్రం" if 17 <= h < 20 else "రాత్రి"
    bn_prefix = "সকাল" if 4 <= h < 12 else "দুপুর" if 12 <= h < 17 else "বিকাল" if 17 <= h < 20 else "রাত"
    ml_prefix = "രാവിലെ" if 4 <= h < 12 else "ഉച്ചയ്ക്ക്" if 12 <= h < 17 else "വൈകിട്ട്" if 17 <= h < 20 else "രാത്രി"

    return {
        "en": f"{h12} {suffix_en}",
        "hi": f"{hi_prefix} {h12} बजे",
        "mr": f"{mr_prefix} {h12} वाजता",
        "ta": f"{ta_prefix} {h12} மணி",
        "te": f"{te_prefix} {h12} గంటలకు",
        "bn": f"{bn_prefix} {h12}টায়",
        "ml": f"{ml_prefix} {h12} മണിക്ക്",
    }


def span(from_h: int, to_h: int, lang: Language) -> str:
    a, b = clock(from_h).get(lang, clock(from_h)["en"]), clock(to_h).get(lang, clock(to_h)["en"])
    joiner = {"en": "to", "hi": "से", "mr": "ते", "ta": "முதல்", "te": "నుండి", "bn": "থেকে", "ml": "മുതൽ"}
    return f"{a} {joiner.get(lang, 'to')} {b}"


# A fisher navigates by "towards the west", not by "WSW".
_DIRECTION_WORDS = {
    "N":  {"en": "north",      "hi": "उत्तर",          "mr": "उत्तर",    "ta": "வடக்கு",     "te": "ఉత్తరం",    "bn": "উত্তর",      "ml": "വടക്ക്"},
    "NE": {"en": "north-east", "hi": "उत्तर-पूर्व",    "mr": "ईशान्य",   "ta": "வடகிழக்கு",  "te": "ఈశాన్యం",   "bn": "উত্তর-পূর্ব","ml": "വടക്ക്-കിഴക്ക്"},
    "E":  {"en": "east",       "hi": "पूर्व",           "mr": "पूर्व",    "ta": "கிழக்கு",    "te": "తూర్పు",    "bn": "পূর্ব",      "ml": "കിഴക്ക്"},
    "SE": {"en": "south-east", "hi": "दक्षिण-पूर्व",   "mr": "आग्नेय",   "ta": "தென்கிழக்கு","te": "ఆగ్నేయం",   "bn": "দক্ষিণ-পূর্ব","ml": "തെക്ക്-കിഴക്ക്"},
    "S":  {"en": "south",      "hi": "दक्षिण",          "mr": "दक्षिण",   "ta": "தெற்கு",     "te": "దక్షిణం",   "bn": "দক্ষিণ",     "ml": "തെക്ക്"},
    "SW": {"en": "south-west", "hi": "दक्षिण-पश्चिम",  "mr": "नैऋत्य",   "ta": "தென்மேற்கு", "te": "నైరుతి",    "bn": "দক্ষিণ-পশ্চিম","ml": "തെക്ക്-പടിഞ്ഞാറ്"},
    "W":  {"en": "west",       "hi": "पश्चिम",          "mr": "पश्चिम",   "ta": "மேற்கு",     "te": "పశ్చిమం",   "bn": "পশ্চিম",     "ml": "പടിഞ്ഞാറ്"},
    "NW": {"en": "north-west", "hi": "उत्तर-पश्चिम",   "mr": "वायव्य",   "ta": "வடமேற்கு",   "te": "వాయవ్యం",   "bn": "উত্তর-পশ্চিম","ml": "വടക്ക്-പടിഞ്ഞാറ്"},
}


def direction_words(bearing: Optional[str], lang: Language) -> str:
    """Collapse a 16-point compass label to a plain 8-point direction word."""
    if not bearing:
        return ""
    b = bearing.upper()
    key = b if b in _DIRECTION_WORDS else b[1:]
    return _pick(_DIRECTION_WORDS.get(key, _DIRECTION_WORDS.get(b[:1], {})), lang)


def sentence(text: str) -> str:
    """Capitalise the first letter without touching the rest."""
    return text[:1].upper() + text[1:] if text else text


# --- how big is a wave, in human terms ------------------------------------
def wave_words(wave_m: Optional[float], lang: Language) -> str:
    if wave_m is None:
        return _pick({"en": "sea height unknown", "hi": "लहरों की जानकारी नहीं",
                      "mr": "लाटांची माहिती नाही", "ta": "கடல் உயரம் தெரியவில்லை",
                      "te": "సముద్ర ఎత్తు తెలియడం లేదు", "bn": "সমুদ্রের উচ্চতা জানা নেই",
                      "ml": "കടലിന്റെ ഉയരം അജ്ഞാതം"}, lang)
    if wave_m < 0.8:
        return _pick({"en": "the sea is calm — small ripples only",
                      "hi": "समुद्र शांत है — छोटी लहरें",
                      "mr": "समुद्र शांत आहे — लहान लाटा",
                      "ta": "கடல் அமைதியாக உள்ளது — சிறு அலைகள் மட்டுமே",
                      "te": "సముద్రం శాంతంగా ఉంది — చిన్న అలలు మాత్రమే",
                      "bn": "সমুদ্র শান্ত — ছোট ঢেউ মাত্র",
                      "ml": "കടൽ ശാന്തമാണ് — ചെറിയ തിരകൾ മാത്രം"}, lang)
    if wave_m < 1.5:
        return _pick({"en": "waves are about knee to waist high",
                      "hi": "लहरें घुटने से कमर तक ऊँची हैं",
                      "mr": "लाटा गुडघ्यापासून कंबरेइतक्या उंच आहेत",
                      "ta": "அலைகள் முட்டி முதல் இடுப்பு வரை உயரமாக உள்ளன",
                      "te": "అలలు మోకాలి నుండి నడుము వరకు ఎత్తు ఉన్నాయి",
                      "bn": "ঢেউ হাঁটু থেকে কোমর পর্যন্ত উঁচু",
                      "ml": "തിരകൾ മുട്ടു മുതൽ അരക്കെട്ട് വരെ ഉയരമുണ്ട്"}, lang)
    if wave_m < 2.5:
        return _pick({"en": "waves are taller than a person — the boat will be thrown about",
                      "hi": "लहरें आदमी से ऊँची हैं — नाव बहुत हिलेगी",
                      "mr": "लाटा माणसापेक्षा उंच आहेत — होडी खूप हलेल",
                      "ta": "அலைகள் மனிதனை விட உயரமாக உள்ளன — படகு மிகவும் ஆடும்",
                      "te": "అలలు మనిషి కంటే ఎత్తుగా ఉన్నాయి — పడవ చాలా ఊగిసలాడుతుంది",
                      "bn": "ঢেউ মানুষের চেয়ে উঁচু — নৌকা খুব দুলবে",
                      "ml": "തിരകൾ ഒരു മനുഷ്യനേക്കാൾ ഉയരമുണ്ട് — ബോട്ട് ഒരുപാട് ഉലയും"}, lang)
    if wave_m < 4.0:
        return _pick({"en": "waves are as tall as a house — very dangerous for a small boat",
                      "hi": "लहरें घर जितनी ऊँची हैं — छोटी नाव के लिए बहुत खतरनाक",
                      "mr": "लाटा घराएवढ्या उंच आहेत — लहान होडीसाठी अत्यंत धोकादायक",
                      "ta": "அலைகள் வீட்டு அளவு உயரமாக உள்ளன — சிறு படகிற்கு மிகவும் ஆபத்து",
                      "te": "అలలు ఒక ఇంత ఎత్తు ఉన్నాయి — చిన్న పడవకు చాలా ప్రమాదకరం",
                      "bn": "ঢেউ বাড়ির মতো উঁচু — ছোট নৌকার জন্য অত্যন্ত বিপজ্জনক",
                      "ml": "തിരകൾ ഒരു വീടിന്റെ ഉയരത്തിലുണ്ട് — ചെറിയ ബോട്ടിന് അതീവ അപകടകരം"}, lang)
    return _pick({"en": "the sea is wild — no small boat can survive this",
                  "hi": "समुद्र बहुत भयंकर है — कोई छोटी नाव नहीं टिकेगी",
                  "mr": "समुद्र अत्यंत खवळलेला आहे — कोणतीही लहान होडी टिकणार नाही",
                  "ta": "கடல் கொந்தளிக்கிறது — சிறு படகு தாங்காது",
                  "te": "సముద్రం విజృంభిస్తోంది — చిన్న పడవ తట్టుకోలేదు",
                  "bn": "সমুদ্র প্রচণ্ড উত্তাল — কোনো ছোট নৌকা টিকবে না",
                  "ml": "കടൽ ഭ്രാന്തൻ — ഒരു ചെറിയ ബോട്ടും പിടിക്കില്ല"}, lang)


def wind_words(wind_kmh: Optional[float], lang: Language) -> str:
    if wind_kmh is None:
        return ""
    if wind_kmh < 15:
        return _pick({"en": "there is barely any wind", "hi": "हवा बहुत कम है",
                      "mr": "वारा फारच कमी आहे", "ta": "காற்று மிகவும் குறைவாக உள்ளது",
                      "te": "గాలి చాలా తక్కువగా ఉంది", "bn": "বাতাস খুব কম",
                      "ml": "കാറ്റ് വളരെ കുറവാണ്"}, lang)
    if wind_kmh < 30:
        return _pick({"en": "there is a steady breeze", "hi": "हवा सामान्य है",
                      "mr": "वारा सामान्य आहे", "ta": "காற்று நிலையாக வீசுகிறது",
                      "te": "గాలి స్థిరంగా వీస్తోంది", "bn": "বাতাস স্বাভাবিক গতিতে বইছে",
                      "ml": "കാറ്റ് സ്ഥിരമായി വീശുന്നു"}, lang)
    if wind_kmh < 50:
        return _pick({"en": "the wind is strong", "hi": "हवा तेज़ है", "mr": "वारा जोरदार आहे",
                      "ta": "காற்று வலுவாக உள்ளது", "te": "గాలి బలంగా ఉంది",
                      "bn": "বাতাস জোরালো", "ml": "കാറ്റ് ശക്തമാണ്"}, lang)
    return _pick({"en": "the wind is dangerously strong", "hi": "हवा बहुत ही खतरनाक तेज़ है",
                  "mr": "वारा अत्यंत धोकादायक जोरात आहे", "ta": "காற்று மிகவும் ஆபத்தான வேகத்தில் உள்ளது",
                  "te": "గాలి ప్రమాదకరమైన వేగంలో ఉంది", "bn": "বাতাস বিপজ্জনকভাবে প্রবল",
                  "ml": "കാറ്റ് അപകടകരമായ വേഗത്തിലാണ്"}, lang)


# --- the headline verdict --------------------------------------------------
GO_LINE = {
    "LOW": {
        "en": "You can go today.",
        "hi": "आप आज जा सकते हैं।",
        "mr": "तुम्ही आज जाऊ शकता.",
        "ta": "நீங்கள் இன்று போகலாம்.",
        "te": "మీరు నేడు వెళ్ళవచ్చు.",
        "bn": "আপনি আজ যেতে পারেন।",
        "ml": "നിങ്ങൾ ഇന്ന് പോകാം.",
    },
    "MODERATE": {
        "en": "You can go, but be careful and stay close to shore.",
        "hi": "आप जा सकते हैं, पर सावधान रहें और किनारे के पास रहें।",
        "mr": "तुम्ही जाऊ शकता, पण काळजी घ्या आणि किनाऱ्याजवळ राहा.",
        "ta": "போகலாம், ஆனால் கவனமாக இருங்கள் மற்றும் கரைக்கு அருகில் இருங்கள்.",
        "te": "వెళ్ళవచ్చు, కానీ జాగ్రత్తగా ఉండండి మరియు తీరానికి దగ్గరగా ఉండండి.",
        "bn": "যেতে পারেন, তবে সতর্ক থাকুন এবং তীরের কাছে থাকুন।",
        "ml": "പോകാം, പക്ഷേ ശ്രദ്ധിക്കണം, കരയോട് അടുത്ത് നിൽക്കണം.",
    },
    "HIGH": {
        "en": "Do not go out today.",
        "hi": "आज समुद्र में मत जाइए।",
        "mr": "आज समुद्रात जाऊ नका.",
        "ta": "இன்று கடலுக்கு செல்லாதீர்கள்.",
        "te": "నేడు సముద్రంలోకి వెళ్లకండి.",
        "bn": "আজ সমুদ্রে যাবেন না।",
        "ml": "ഇന്ന് കടലിലേക്ക് പോകരുത്.",
    },
    "EXTREME": {
        "en": "Do not go out. Stay on land and keep your boat tied.",
        "hi": "बिल्कुल मत जाइए। ज़मीन पर रहें और नाव बाँधकर रखें।",
        "mr": "अजिबात जाऊ नका. जमिनीवर राहा आणि होडी बांधून ठेवा.",
        "ta": "செல்லாதீர்கள். நிலத்தில் இருங்கள் மற்றும் படகை கட்டி வையுங்கள்.",
        "te": "వెళ్లకండి. నేలపై ఉండండి మరియు పడవను కట్టివేయండి.",
        "bn": "যাবেন না। মাটিতে থাকুন এবং নৌকা বেঁধে রাখুন।",
        "ml": "പോകരുത്. കരയിൽ ഇരിക്കുക, ബോട്ട് കെട്ടിയിടുക.",
    },
}

CATCH_WORD = {
    "very_good": {
        "en": "very good chance of fish", "hi": "मछली मिलने की बहुत अच्छी उम्मीद",
        "mr": "मासे मिळण्याची खूप चांगली शक्यता",
        "ta": "மீன் கிடைக்கும் வாய்ப்பு மிகவும் அதிகம்",
        "te": "చేపలు దొరికే అవకాశం చాలా ఎక్కువ",
        "bn": "মাছ পাওয়ার সম্ভাবনা খুব বেশি",
        "ml": "മീൻ ലഭിക്കാനുള്ള സാധ്യത വളരെ അധികം",
    },
    "good": {
        "en": "good chance of fish", "hi": "मछली मिलने की अच्छी उम्मीद",
        "mr": "मासे मिळण्याची चांगली शक्यता",
        "ta": "மீன் கிடைக்கும் நல்ல வாய்ப்பு",
        "te": "చేపలు దొరికే మంచి అవకాశం",
        "bn": "মাছ পাওয়ার ভালো সম্ভাবনা",
        "ml": "മീൻ ലഭിക്കാനുള്ള നല്ല സാധ്യത",
    },
    "fair": {
        "en": "some chance of fish", "hi": "मछली मिलने की कुछ उम्मीद",
        "mr": "मासे मिळण्याची थोडी शक्यता",
        "ta": "மீன் கிடைக்கும் சிறிய வாய்ப்பு",
        "te": "చేపలు దొరికే కొంచెం అవకాశం",
        "bn": "মাছ পাওয়ার কিছু সম্ভাবনা",
        "ml": "മീൻ ലഭിക്കാനുള്ള ചെറിയ സാധ്യത",
    },
    "poor": {
        "en": "low chance of fish", "hi": "मछली मिलने की कम उम्मीद",
        "mr": "मासे मिळण्याची कमी शक्यता",
        "ta": "மீன் கிடைக்கும் வாய்ப்பு குறைவு",
        "te": "చేపలు దొరికే అవకాశం తక్కువ",
        "bn": "মাছ পাওয়ার সম্ভাবনা কম",
        "ml": "മീൻ ലഭിക്കാനുള്ള സാധ്യത കുറവ്",
    },
}


def build(*, lang: Language, risk_category: str, official_warning: bool,
          wave_m: Optional[float], wind_kmh: Optional[float],
          improve_hour: Optional[int], zones: Sequence[Dict],
          closed_zones: Sequence[Dict], duration: Optional[Dict],
          best_window: Optional[Sequence[int]], forecast: Sequence[Dict]) -> List[str]:
    """The whole advisory, as short spoken-style sentences."""
    lines: List[str] = []
    if lang not in _SUPPORTED:
        lang = "en"

    def _l(d: Dict[str, str]) -> str:
        return _pick(d, lang)

    # 1. safety first, always
    go = GO_LINE.get(risk_category, GO_LINE["MODERATE"])
    lines.append(_l(go))
    sea = wave_words(wave_m, lang)
    wind = wind_words(wind_kmh, lang)
    lines.append(sentence(f"{sea}." if not wind else f"{sea}, {wind}."))

    if official_warning:
        lines.append(_l({
            "en": "The government has put out a warning for this coast. Please follow it.",
            "hi": "सरकार ने इस तट के लिए चेतावनी दी है। कृपया उसका पालन करें।",
            "mr": "सरकारने या किनाऱ्यासाठी इशारा दिला आहे. कृपया तो पाळा.",
            "ta": "அரசு இந்த கடற்கரைக்கு எச்சரிக்கை விடுத்துள்ளது. தயவுசெய்து அதை பின்பற்றவும்.",
            "te": "ప్రభుత్వం ఈ తీరానికి హెచ్చరిక జారీ చేసింది. దయచేసి దాన్ని పాటించండి.",
            "bn": "সরকার এই উপকূলের জন্য সতর্কতা জারি করেছে। অনুগ্রহ করে সেটি মেনে চলুন।",
            "ml": "ഈ തീരത്തിനായി സർക്കാർ മുന്നറിയിപ്പ് നൽകിയിട്ടുണ്ട്. ദയവായി അത് പാലിക്കുക.",
        }))

    if risk_category in ("HIGH", "EXTREME") and improve_hour is not None:
        c = clock(improve_hour)
        lines.append(_l({
            "en": f"The sea should settle after {c['en']}. Ask me again then.",
            "hi": f"{c['hi']} के बाद समुद्र शांत होना चाहिए। तब दोबारा पूछें।",
            "mr": f"{c['mr']} नंतर समुद्र शांत व्हायला हवा. तेव्हा पुन्हा विचारा.",
            "ta": f"கடல் {c.get('ta', c['en'])} க்கு பிறகு அமைதியாகும். அப்போது மீண்டும் கேளுங்கள்.",
            "te": f"సముద్రం {c.get('te', c['en'])} తర్వాత శాంతిస్తుంది. అప్పుడు మళ్ళీ అడగండి.",
            "bn": f"{c.get('bn', c['en'])} র পরে সমুদ্র শান্ত হবে। তখন আবার জিজ্ঞেস করুন।",
            "ml": f"{c.get('ml', c['en'])} ക്ക് ശേഷം കടൽ ശാന്തമാകും. അപ്പോൾ വീണ്ടും ചോദിക്കുക.",
        }))

    # 2. closed areas, with the hours spelled out
    for z in closed_zones:
        window = z.get("window")
        name = z.get("name", "restricted area")
        if window:
            a, b = window.split("-")
            phrase = span(int(a.split(":")[0]), int(b.split(":")[0]), lang)
            lines.append(_l({
                "en": f"Do not go into the red area on the map from {phrase} today. It is closed then.",
                "hi": f"नक्शे के लाल हिस्से में {phrase} के बीच मत जाइए। उस समय वह बंद रहता है।",
                "mr": f"नकाशावरील लाल भागात {phrase} या वेळेत जाऊ नका. त्या वेळी तो बंद असतो.",
                "ta": f"இன்று {phrase} நேரத்தில் வரைபடத்தில் சிவப்பு பகுதிக்கு செல்லாதீர்கள். அது அப்போது மூடியிருக்கும்.",
                "te": f"ఈ రోజు {phrase} సమయంలో మ్యాప్‌లోని ఎరుపు ప్రాంతానికి వెళ్లకండి. ఆ సమయంలో అది మూసివేయబడుతుంది.",
                "bn": f"আজ {phrase} এর মধ্যে মানচিত্রের লাল এলাকায় যাবেন না। সেই সময় এটি বন্ধ থাকে।",
                "ml": f"ഇന്ന് {phrase} സമയത്ത് ഭൂപടത്തിലെ ചുവന്ന ഭാഗത്ത് പോകരുത്. ആ സമയം അത് അടഞ്ഞിരിക്കും.",
            }))
        else:
            lines.append(_l({
                "en": f"Never enter the red area on the map — {name}. Boats are stopped and fined there.",
                "hi": f"नक्शे के लाल हिस्से में कभी मत जाइए — {name}। वहाँ नाव पकड़ी जाती है।",
                "mr": f"नकाशावरील लाल भागात कधीही जाऊ नका — {name}. तिथे होडी पकडली जाते.",
                "ta": f"வரைபடத்தில் சிவப்பு பகுதிக்கு ஒருபோதும் செல்லாதீர்கள் — {name}. அங்கு படகுகள் தடுத்து அபராதம் விதிக்கப்படும்.",
                "te": f"మ్యాప్‌లోని ఎరుపు ప్రాంతంలో ఎప్పుడూ వెళ్లకండి — {name}. అక్కడ పడవలు ఆపివేయబడి జరిమానా విధించబడతాయి.",
                "bn": f"মানচিত্রের লাল এলাকায় কখনো যাবেন না — {name}. সেখানে নৌকা আটক করে জরিমানা করা হয়।",
                "ml": f"ഭൂപടത്തിലെ ചുവന്ന ഭാഗത്ത് ഒരിക്കലും പോകരുത് — {name}. അവിടെ ബോട്ടുകൾ തടഞ്ഞ് പിഴ ഈടാക്കും.",
            }))

    # 3. where the fish are
    good = [z for z in zones if z.get("rating") in ("very_good", "good")]
    if good:
        numbers = ", ".join(str(z["rank"]) for z in good[:3])
        top = next((z for z in zones if z.get("recommended")), good[0])
        lines.append(_l({
            "en": f"Areas {numbers} on the map are your best chances today.",
            "hi": f"नक्शे पर {numbers} नंबर की जगहें आज सबसे अच्छी हैं।",
            "mr": f"नकाशावरील {numbers} क्रमांकाच्या जागा आज सर्वात चांगल्या आहेत.",
            "ta": f"வரைபடத்தில் {numbers} எண் பகுதிகள் இன்று சிறந்தவை.",
            "te": f"మ్యాప్‌లో {numbers} నంబర్ ప్రాంతాలు ఈ రోజు మీకు అత్యుత్తమ అవకాశాలు.",
            "bn": f"মানচিত্রে {numbers} নং এলাকাগুলো আজ আপনার সেরা সুযোগ।",
            "ml": f"ഭൂപടത്തിൽ {numbers} നമ്പർ ഭാഗങ്ങൾ ഇന്ന് ഏറ്റവും നല്ലവ.",
        }))
        where = direction_words(top.get("bearing"), lang)
        cw = CATCH_WORD[top["rating"]]
        cw_lang = _pick(cw, lang)
        lines.append(_l({
            "en": f"Area {top['rank']} is about {round(top['distance_km'])} kilometres towards the {where} — {cw['en']} there.",
            "hi": f"जगह {top['rank']} यहाँ से लगभग {round(top['distance_km'])} किलोमीटर {where} की ओर है — वहाँ {cw['hi']} है।",
            "mr": f"जागा {top['rank']} इथून अंदाजे {round(top['distance_km'])} किलोमीटर {where} दिशेला आहे — तिथे {cw['mr']} आहे.",
            "ta": f"பகுதி {top['rank']} இங்கிருந்து சுமார் {round(top['distance_km'])} கிலோமீட்டர் {where} திசையில் — அங்கு {cw_lang}.",
            "te": f"ప్రాంతం {top['rank']} ఇక్కడ నుండి సుమారు {round(top['distance_km'])} కిలోమీటర్లు {where} దిశలో — అక్కడ {cw_lang}.",
            "bn": f"এলাকা {top['rank']} এখান থেকে প্রায় {round(top['distance_km'])} কিলোমিটার {where} দিকে — সেখানে {cw_lang}।",
            "ml": f"ഭാഗം {top['rank']} ഇവിടെ നിന്ന് ഏകദേശം {round(top['distance_km'])} കിലോമീറ്റർ {where} ദിശയിൽ — അവിടെ {cw_lang}.",
        }))
    elif zones:
        lines.append(_l({
            "en": "None of the nearby areas look good today. Fishing will be hard.",
            "hi": "आज आसपास की कोई जगह अच्छी नहीं लग रही। मछली मिलना मुश्किल होगा।",
            "mr": "आज जवळपासची कोणतीही जागा चांगली दिसत नाही. मासे मिळणे कठीण होईल.",
            "ta": "இன்று அருகிலுள்ள எந்த பகுதியும் நல்லதாக இல்லை. மீன்பிடித்தல் கஷ்டமாக இருக்கும்.",
            "te": "ఈ రోజు సమీప ప్రాంతాలు ఏదీ మంచిగా కనిపించడం లేదు. చేపలు పట్టడం కష్టంగా ఉంటుంది.",
            "bn": "আজ কাছের কোনো এলাকা ভালো দেখাচ্ছে না। মাছ ধরা কঠিন হবে।",
            "ml": "ഇന്ന് അടുത്ത ഒരു ഭാഗവും നല്ലതായി കാണുന്നില്ല. മത്സ്യബന്ധനം ബുദ്ധിമുട്ടാകും.",
        }))

    # 4. best hours to be on the water
    if best_window and len(best_window) == 2:
        bw_span = span(best_window[0], best_window[1], lang)
        lines.append(_l({
            "en": f"The best time to fish is {span(best_window[0], best_window[1], 'en')}.",
            "hi": f"मछली पकड़ने का सबसे अच्छा समय {span(best_window[0], best_window[1], 'hi')} है।",
            "mr": f"मासेमारीसाठी सर्वोत्तम वेळ {span(best_window[0], best_window[1], 'mr')} आहे.",
            "ta": f"மீன் பிடிக்க சிறந்த நேரம் {bw_span}.",
            "te": f"చేపలు పట్టడానికి అత్యుత్తమ సమయం {bw_span}.",
            "bn": f"মাছ ধরার সেরা সময় {bw_span}।",
            "ml": f"മത്സ്യബന്ധനത്തിന് ഏറ്റവും അനുകൂലമായ സമയം {bw_span}.",
        }))

    # 5. how long to stay
    if duration and duration.get("feasible"):
        hours = duration["recommended_hours"]
        trip = duration["total_trip_hours"]
        lines.append(_l({
            "en": f"Stay there about {hours:g} hours. With travel, the whole trip is roughly {trip:g} hours.",
            "hi": f"वहाँ लगभग {hours:g} घंटे रुकिए। आने-जाने के साथ पूरी यात्रा करीब {trip:g} घंटे की होगी।",
            "mr": f"तिथे अंदाजे {hours:g} तास थांबा. ये-जा धरून संपूर्ण फेरी साधारण {trip:g} तासांची होईल.",
            "ta": f"அங்கு சுமார் {hours:g} மணி நேரம் இருங்கள். பயணம் உட்பட முழு பயணமும் சுமார் {trip:g} மணி நேரம்.",
            "te": f"అక్కడ సుమారు {hours:g} గంటలు ఉండండి. ప్రయాణం కలిపి మొత్తం సుమారు {trip:g} గంటలు.",
            "bn": f"সেখানে প্রায় {hours:g} ঘণ্টা থাকুন। যাতায়াত মিলিয়ে পুরো যাত্রা প্রায় {trip:g} ঘণ্টার।",
            "ml": f"അവിടെ ഏകദേശം {hours:g} മണിക്കൂർ നിൽക്കുക. യാത്ര ഉൾപ്പെടെ ആകെ ഏകദേശം {trip:g} മണിക്കൂർ.",
        }))
        if duration.get("limited_by_weather"):
            lines.append(_l({
                "en": "Come back earlier than usual — the weather turns after that.",
                "hi": "सामान्य से जल्दी लौट आइए — उसके बाद मौसम बिगड़ेगा।",
                "mr": "नेहमीपेक्षा लवकर परत या — त्यानंतर हवामान बिघडेल.",
                "ta": "வழக்கத்தை விட முன்பே திரும்பி வாருங்கள் — அதற்குப் பிறகு வானிலை மோசமாகும்.",
                "te": "సాధారణం కంటే ముందే తిరిగి రండి — తర్వాత వాతావరణం మారుతుంది.",
                "bn": "স্বাভাবিকের চেয়ে আগে ফিরে আসুন — এরপর আবহাওয়া খারাপ হবে।",
                "ml": "പതിവിലും നേരത്തേ തിരിച്ചുവരൂ — അതിനുശേഷം കാലാവസ്ഥ മോശമാകും.",
            }))
    elif duration is not None:
        lines.append(_l({
            "en": "There is not enough safe time today to make the trip worthwhile.",
            "hi": "आज इतना सुरक्षित समय नहीं है कि जाना ठीक रहे।",
            "mr": "आज फेरी करण्याइतका सुरक्षित वेळ नाही.",
            "ta": "இன்று பயணத்தை மதிப்புமிக்கதாக்க போதுமான பாதுகாப்பான நேரம் இல்லை.",
            "te": "ఈ రోజు ప్రయాణాన్ని సార్థకం చేసుకోవడానికి తగినంత సురక్షిత సమయం లేదు.",
            "bn": "আজ যাত্রা সার্থক করার মতো যথেষ্ট নিরাপদ সময় নেই।",
            "ml": "ഇന്ന് യാത്ര ഫലപ്രദമാക്കാൻ ആവശ്യത്തിന് സുരക്ഷിത സമയം ഇല്ല.",
        }))

    # 6. next two days
    _DAY = {
        "en": {1: "Tomorrow",    2: "The day after"},
        "hi": {1: "कल",          2: "परसों"},
        "mr": {1: "उद्या",        2: "परवा"},
        "ta": {1: "நாளை",        2: "நாளை மறுநாள்"},
        "te": {1: "రేపు",         2: "ఎల్లుండి"},
        "bn": {1: "আগামীকাল",    2: "পরশু"},
        "ml": {1: "നാളെ",        2: "മറ്റന്നാൾ"},
    }
    _CALMER = {"en": "calmer",   "hi": "शांत",      "mr": "शांत",      "ta": "அமைதியாக",    "te": "ప్రశాంతంగా", "bn": "শান্ত",    "ml": "ശാന്തം"}
    _ROUGHER = {"en": "rougher", "hi": "ज़्यादा खराब","mr": "अधिक खवळलेला","ta": "கடுமையாக",  "te": "కఠినంగా",    "bn": "উত্তাল",   "ml": "കഠിനം"}

    for f in forecast[1:3]:
        offset = f.get("day_offset", 1)
        day_lut = _DAY.get(lang, _DAY["en"])
        day = day_lut.get(offset, str(offset))
        cw_f = _pick(CATCH_WORD[f["rating"]], lang)
        sea_word = _pick(_CALMER if f["calmer"] else _ROUGHER, lang)
        lines.append(f"{day}: {cw_f}, " + _l({
            "en": f"and the sea will be {_CALMER['en'] if f['calmer'] else _ROUGHER['en']}.",
            "hi": f"और समुद्र {_CALMER['hi'] if f['calmer'] else _ROUGHER['hi']} रहेगा।",
            "mr": f"आणि समुद्र {_CALMER['mr'] if f['calmer'] else _ROUGHER['mr']} असेल.",
            "ta": f"கடல் {sea_word} இருக்கும்.",
            "te": f"సముద్రం {sea_word} ఉంటుంది.",
            "bn": f"সমুদ্র {sea_word} থাকবে।",
            "ml": f"കടൽ {sea_word} ആയിരിക്കും.",
        }))

    # 7. the promise we never break
    lines.append(_l({
        "en": "This is our best guess from the data — it is not a promise of fish. Always follow the Coast Guard and the government warning.",
        "hi": "यह आँकड़ों से लगाया गया अनुमान है — मछली की गारंटी नहीं। तटरक्षक बल और सरकारी चेतावनी का पालन ज़रूर करें।",
        "mr": "हा माहितीवरून काढलेला अंदाज आहे — माशांची हमी नाही. तटरक्षक दल आणि सरकारी इशारा नेहमी पाळा.",
        "ta": "இது தரவுகளிலிருந்து எடுக்கப்பட்ட சிறந்த அனுமானம் — மீன் கிடைக்கும் என்ற உறுதிமொழி அல்ல. கடலோர காவல்படை மற்றும் அரசு எச்சரிக்கையை எப்போதும் பின்பற்றுங்கள்.",
        "te": "ఇది డేటా ఆధారంగా మా అత్యుత్తమ అంచనా — చేపల లభ్యతకు హామీ కాదు. కోస్ట్ గార్డ్ మరియు ప్రభుత్వ హెచ్చరికను ఎల్లప్పుడూ పాటించండి.",
        "bn": "এটি তথ্যের উপর ভিত্তি করে আমাদের সেরা অনুমান — মাছ পাওয়ার গ্যারান্টি নয়। সর্বদা কোস্ট গার্ড এবং সরকারি সতর্কতা মেনে চলুন।",
        "ml": "ഇത് ഡേറ്റ അടിസ്ഥാനമാക്കിയ ഞങ്ങളുടെ ഏറ്റവും നല്ല ഊഹം — മത്സ്യ ലഭ്യതയ്ക്ക് ഉറപ്പ് നൽകുന്നില്ല. കോസ്റ്റ് ഗാർഡ്, സർക്കാർ മുന്നറിയിപ്പ് എപ്പോഴും പാലിക്കുക.",
    }))

    return lines
