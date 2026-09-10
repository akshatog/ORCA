"""Language detection and response templates for Indian Coastal Languages.

Supports:
  - English (en)
  - Hindi (hi)
  - Marathi (mr)
  - Tamil (ta)
  - Telugu (te)
  - Bengali (bn)
  - Malayalam (ml)
  - Gujarati (gu)
  - Kannada (kn)
  - Odia (or)

Rules:
  * numeric values are NEVER localised into other numeral systems — "2.4 m"
    stays "2.4 m" so numbers cannot be misread on a moving vessel;
  * detection is script-range based (Unicode blocks), working offline with 0ms latency.
"""
from __future__ import annotations

import re
from typing import Dict, List

from ..schemas import Language

# Unicode script ranges for Indian regional languages
TAMIL = re.compile(r"[\u0B80-\u0BFF]")
TELUGU = re.compile(r"[\u0C00-\u0C7F]")
BENGALI = re.compile(r"[\u0980-\u09FF]")
MALAYALAM = re.compile(r"[\u0D00-\u0D7F]")
GUJARATI = re.compile(r"[\u0A80-\u0AFF]")
KANNADA = re.compile(r"[\u0C80-\u0CFF]")
ODIA = re.compile(r"[\u0B00-\u0B7F]")
DEVANAGARI = re.compile(r"[\u0900-\u097F]")

# Words that separate Marathi from Hindi (both use Devanagari script).
MARATHI_MARKERS = ["आहे", "शकतो", "शकते", "मासेमारी", "काय", "नाही", "सुरक्षित का",
                   "समुद्रात", "होडी", "मला", "कुठे", "आज", "उद्या सकाळी", "मार्ग"]
HINDI_MARKERS = ["है", "सकता", "सकती", "मछली", "क्या", "नहीं", "समुद्र में",
                 "नाव", "मुझे", "कहाँ", "कहां", "रास्ता"]


def detect_language(text: str) -> Language:
    """Detect language via zero-dependency Unicode script recognition and lexical markers."""
    if not text or not text.strip():
        return "en"

    if TAMIL.search(text):
        return "ta"
    if TELUGU.search(text):
        return "te"
    if BENGALI.search(text):
        return "bn"
    if MALAYALAM.search(text):
        return "ml"
    if GUJARATI.search(text):
        return "gu"
    if KANNADA.search(text):
        return "kn"
    if ODIA.search(text):
        return "or"
    if DEVANAGARI.search(text):
        mr = sum(1 for w in MARATHI_MARKERS if w in text)
        hi = sum(1 for w in HINDI_MARKERS if w in text)
        if mr > hi:
            return "mr"
        if hi > mr:
            return "hi"
        return "mr"  # Default Devanagari to Marathi (pilot coast)

    return "en"


# --------------------------------------------------------------------------
# Phrase book
# --------------------------------------------------------------------------
T: Dict[str, Dict[str, str]] = {
    "verdict_low": {
        "en": "Conditions look safe",
        "hi": "स्थिति सुरक्षित लग रही है",
        "mr": "परिस्थिती सुरक्षित दिसते",
        "ta": "சூழ்நிலைகள் பாதுகாப்பாக உள்ளன",
        "te": "పరిస్థితులు సురక్షితంగా ఉన్నాయి",
        "bn": "পরিস্থিতি অনুকূল ও নিরাপদ",
        "ml": "സാഹചര്യങ്ങൾ സുരക്ഷിതമാണ്",
    },
    "verdict_moderate": {
        "en": "Go with caution",
        "hi": "सावधानी से जाएँ",
        "mr": "सावधगिरीने जा",
        "ta": "எச்சரிக்கையுடன் செல்லுங்கள்",
        "te": "జాగ్రత్తగా వెళ్ళండి",
        "bn": "সতর্কতার সাথে যান",
        "ml": "ജാഗ്രതയോടെ പോകുക",
    },
    "verdict_high": {
        "en": "High risk — not recommended",
        "hi": "जोखिम अधिक है — जाने की सलाह नहीं",
        "mr": "धोका जास्त आहे — जाऊ नका",
        "ta": "அதிக ஆபத்து — கடலுக்கு செல்ல பரிந்துரைக்கப்படவில்லை",
        "te": "అధిక ప్రమాదం — వెళ్లడం సిఫార్సు చేయబడలేదు",
        "bn": "উচ্চ ঝুঁকি — সমুদ্রে যাওয়া অনুচিত",
        "ml": "ഉയർന്ന അപകടസാധ്യത — പോകാൻ ശുപാർശ ചെയ്യുന്നില്ല",
    },
    "verdict_extreme": {
        "en": "EXTREME RISK — do not go to sea",
        "hi": "अत्यधिक जोखिम — समुद्र में न जाएँ",
        "mr": "अत्यंत धोका — समुद्रात जाऊ नका",
        "ta": "அதிதீவிர ஆபத்து — கடலுக்குச் செல்லாதீர்கள்",
        "te": "అత్యంత ప్రమాదకరం — సముద్రంలోకి వెళ్లవద్దు",
        "bn": "চরম বিপদ — সমুদ্রে যাবেন না",
        "ml": "അതീവ അപകടസാധ്യത — കടലിൽ പോകരുത്",
    },
    "based_on": {
        "en": "Based on available data",
        "hi": "उपलब्ध आँकड़ों के आधार पर",
        "mr": "उपलब्ध माहितीच्या आधारे",
        "ta": "கிடைக்கக்கூடிய தரவுகளின் அடிப்படையில்",
        "te": "అందుబాటులో ఉన్న డేటా ఆధారంగా",
        "bn": "উপলব্ধ তথ্যের ভিত্তিতে",
        "ml": "ലഭ്യമായ വിവരങ്ങളുടെ അടിസ്ഥാനത്തിൽ",
    },
    "risk_score": {
        "en": "Risk score",
        "hi": "जोखिम स्कोर",
        "mr": "धोका गुण",
        "ta": "ஆபத்து மதிப்பீடு",
        "te": "రిస్క్ స్కోరు",
        "bn": "ঝুঁকির মাত্রা",
        "ml": "അപകട സ്കോർ",
    },
    "why": {
        "en": "Main reasons",
        "hi": "मुख्य कारण",
        "mr": "मुख्य कारणे",
        "ta": "முக்கிய காரணங்கள்",
        "te": "ప్రధాన కారణాలు",
        "bn": "প্রধান কারণসমূহ",
        "ml": "പ്രധാന കാരണങ്ങൾ",
    },
    "official_warning": {
        "en": "An official warning is in force. Please follow IMD / INCOIS and Coast Guard instructions.",
        "hi": "आधिकारिक चेतावनी लागू है। कृपया IMD / INCOIS और तटरक्षक बल के निर्देशों का पालन करें।",
        "mr": "अधिकृत इशारा लागू आहे. कृपया IMD / INCOIS आणि तटरक्षक दलाच्या सूचना पाळा.",
        "ta": "அதிகாரப்பூர்வ எச்சரிக்கை நடைமுறையில் உள்ளது. தயவுசெய்து IMD / INCOIS மற்றும் கடலோர காவல்படை வழிமுறைகளைப் பின்பற்றவும்.",
        "te": "అధికారిక హెచ్చరిక అమలులో ఉంది. దయచేసి IMD / INCOIS మరియు కోస్ట్ గార్డ్ సూచనలను పాటించండి.",
        "bn": "সরকারি সতর্কবার্তা জারি রয়েছে। অনুগ্রহ করে IMD / INCOIS এবং উপকূলরক্ষী বাহিনীর নির্দেশ মেনে চলুন।",
        "ml": "ഔദ്യോഗിക മുന്നറിയിപ്പ് നിലവിലുണ്ട്. IMD / INCOIS, കോസ്റ്റ് ഗാർഡ് നിർദ്ദേശങ്ങൾ പാലിക്കുക.",
    },
    "improves_at": {
        "en": "Conditions are expected to improve after {hour}:00. Ask me again then.",
        "hi": "{hour}:00 बजे के बाद स्थिति सुधरने की संभावना है। तब दोबारा पूछें।",
        "mr": "{hour}:00 नंतर परिस्थिती सुधारण्याची शक्यता आहे. तेव्हा पुन्हा विचारा.",
        "ta": "{hour}:00 மணிக்கு பிறகு சூழல் சீரடையும் என எதிர்பார்க்கப்படுகிறது. அப்போது மீண்டும் கேளுங்கள்.",
        "te": "{hour}:00 తర్వాత పరిస్థితులు మెరుగుపడే అవకాశం ఉంది. అప్పుడు మళ్ళీ అడగండి.",
        "bn": "{hour}:00 টার পর পরিস্থিতির উন্নতির সম্ভাবনা রয়েছে। তখন আবার যোগাযোগ করুন।",
        "ml": "{hour}:00 ന് ശേഷം കാലാവസ്ഥ മെച്ചപ്പെടുമെന്ന് പ്രതീക്ഷിക്കുന്നു. പിന്നീട് വീണ്ടും പരിശോധിക്കുക.",
    },
    "no_improvement": {
        "en": "Conditions are not expected to improve today.",
        "hi": "आज स्थिति सुधरने की संभावना नहीं है।",
        "mr": "आज परिस्थिती सुधारण्याची शक्यता नाही.",
        "ta": "இன்று சூழல் சீரடைய வாய்ப்பில்லை.",
        "te": "ఈ రోజు పరిస్థితులు మెరుగయ్యే అవకాశం లేదు.",
        "bn": "আজ আবহাওয়া উন্নতির সম্ভাবনা নেই।",
        "ml": "ഇന്ന് കാലാവസ്ഥ മെച്ചപ്പെടുമെന്ന് പ്രതീക്ഷിക്കുന്നില്ല.",
    },
    "pfz_intro": {
        "en": "Nearest potential fishing zones",
        "hi": "निकटतम संभावित मत्स्य क्षेत्र",
        "mr": "जवळची संभाव्य मासेमारी क्षेत्रे",
        "ta": "அருகிலுள்ள சாத்தியமான மீன்பிடி பகுதிகள்",
        "te": "సమీప సంభావ్య చేపల వేట ప్రాంతాలు",
        "bn": "নিকটবর্তী সম্ভাব্য মাছ ধরার অঞ্চল (PFZ)",
        "ml": "അടുത്തുള്ള മത്സ്യലഭ്യത സാധ്യതയുള്ള മേഖലകൾ",
    },
    "pfz_note": {
        "en": "A potential fishing zone is a scientifically likely area — it is not a guarantee of fish.",
        "hi": "संभावित मत्स्य क्षेत्र वैज्ञानिक रूप से संभावित क्षेत्र है — मछली की गारंटी नहीं।",
        "mr": "संभाव्य मासेमारी क्षेत्र म्हणजे शास्त्रीयदृष्ट्या शक्यता असलेला भाग — माशांची हमी नाही.",
        "ta": "சாத்தியமான மீன்பிடி மண்டலம் என்பது அறிவியல் பூர்வமாக கணிக்கப்பட்ட பகுதி — மீன்களுக்கு உத்தரவாதம் இல்லை.",
        "te": "సంభావ్య చేపల వేట ప్రాంతం శాస్త్రీయంగా అంచనా వేయబడింది — చేపల లభ్యతకు హామీ లేదు.",
        "bn": "সম্ভাব্য মৎস্য অঞ্চল বৈজ্ঞানিকভাবে অনুমিত — মাছ পাওয়ার নিশ্চয়তা নয়।",
        "ml": "ശാസ്ത്രീയമായി കണ്ടെത്തിയ മത്സ്യസാധ്യതാ മേഖലയാണിത് — മീൻ ലഭ്യതയ്ക്ക് ഉറപ്പില്ല.",
    },
    "route_intro": {
        "en": "Safest route",
        "hi": "सबसे सुरक्षित रास्ता",
        "mr": "सर्वात सुरक्षित मार्ग",
        "ta": "மிகவும் பாதுகாப்பான பாதை",
        "te": "అత్యంత సురక్షితమైన మార్గం",
        "bn": "সবচেয়ে নিরাপদ পথ",
        "ml": "ഏറ്റവും സുരക്ഷിതമായ വഴി",
    },
    "route_detail": {
        "en": "{distance} km, about {eta}, avoiding restricted areas.",
        "hi": "{distance} किमी, लगभग {eta}, प्रतिबंधित क्षेत्रों से बचते हुए।",
        "mr": "{distance} किमी, अंदाजे {eta}, प्रतिबंधित क्षेत्रे टाळून.",
        "ta": "{distance} கி.மீ, சுமார் {eta}, தடைசெய்யப்பட்ட பகுதிகளைத் தவிர்க்கிறது.",
        "te": "{distance} కి.మీ, సుమారు {eta}, నిషేధిత ప్రాంతాలను నివారిస్తుంది.",
        "bn": "{distance} কিমি, আনুমানিক {eta}, নিষিদ্ধ এলাকা এড়িয়ে।",
        "ml": "{distance} കി.മീ, ഏകദേശം {eta}, നിയന്ത്രിത മേഖലകൾ ഒഴിവാക്കി.",
    },
    "geofence_warn": {
        "en": "WARNING: {zone} is {distance} km away.",
        "hi": "चेतावनी: {zone} {distance} किमी दूर है।",
        "mr": "इशारा: {zone} {distance} किमी अंतरावर आहे.",
        "ta": "எச்சரிக்கை: {zone} {distance} கி.மீ தொலைவில் உள்ளது.",
        "te": "హెచ్చరిక: {zone} {distance} కి.మీ దూరంలో ఉంది.",
        "bn": "সতর্কতা: {zone} {distance} কিমি দূরে রয়েছে।",
        "ml": "മുന്നറിയിപ്പ്: {zone} {distance} കി.മീ അകലെയാണ്.",
    },
    "geofence_inside": {
        "en": "ALERT: you are inside {zone}. Leave the area immediately.",
        "hi": "अलर्ट: आप {zone} के भीतर हैं। तुरंत क्षेत्र छोड़ें।",
        "mr": "सतर्कता: तुम्ही {zone} मध्ये आहात. ताबडतोब क्षेत्र सोडा.",
        "ta": "எச்சரிக்கை: நீங்கள் {zone} எல்லைக்குள் இருக்கிறீர்கள். உடனே வெளியேறவும்.",
        "te": "హెచ్చరిక: మీరు {zone} లోపల ఉన్నారు. వెంటనే ఆ ప్రాంతం నుండి బయటకు రండి.",
        "bn": "সতর্কতা: আপনি {zone} এর ভেতরে রয়েছেন। অবিলম্বে এলাকা ত্যাগ করুন।",
        "ml": "ജാഗ്രത: നിങ്ങൾ {zone} പരിധിക്കുള്ളിലാണ്. ഉടൻ പ്രദേശം വിടുക.",
    },
    "sources": {
        "en": "Sources",
        "hi": "स्रोत",
        "mr": "स्रोत",
        "ta": "ஆதாரங்கள்",
        "te": "మూలాలు",
        "bn": "উৎস",
        "ml": "ഉറവിടങ്ങൾ",
    },
    "updated": {
        "en": "Updated",
        "hi": "अपडेट",
        "mr": "अपडेट",
        "ta": "புதுப்பிக்கப்பட்டது",
        "te": "నవీకరించబడింది",
        "bn": "আপডেট",
        "ml": "അപ്ഡേറ്റ് ചെയ്തത്",
    },
    "demo_mode": {
        "en": "Demo / simulated data — not a live government feed.",
        "hi": "डेमो / नकली आँकड़े — यह सरकारी लाइव फ़ीड नहीं है।",
        "mr": "डेमो / नमुना माहिती — हा सरकारी थेट स्रोत नाही.",
        "ta": "மாதிரி தரவு — நேரலை அரசு அறிவிப்பு அல்ல.",
        "te": "డెమో సమాచారం — ప్రత్యక్ష ప్రభుత్వ ఫీడ్ కాదు.",
        "bn": "ডেমো তথ্য — সরকারি লাইভ তথ্য নয়।",
        "ml": "ഡെമോ വിവരങ്ങൾ — തത്സമയ സർക്കാർ ഫീഡ് അല്ല.",
    },
    "unavailable": {
        "en": "Ocean forecast unavailable for this location.",
        "hi": "इस स्थान के लिए समुद्री पूर्वानुमान उपलब्ध नहीं है।",
        "mr": "या ठिकाणासाठी समुद्री अंदाज उपलब्ध नाही.",
        "ta": "இந்த இடத்திற்கான கடல்சார் முன்னறிவிப்பு கிடைக்கவில்லை.",
        "te": "ఈ ప్రదేశానికి సముద్ర సూచన అందుబాటులో లేదు.",
        "bn": "এই স্থানের জন্য সামুদ্রিক পূর্বাভাস উপলব্ধ নেই।",
        "ml": "ഈ സ്ഥലത്തെ സമുദ്ര പ്രവചനം ലഭ്യമല്ല.",
    },
    "hours": {
        "en": "h",
        "hi": "घं",
        "mr": "तास",
        "ta": "மணி",
        "te": "గం",
        "bn": "ঘণ্টা",
        "ml": "മണിക്കൂർ",
    },
    "minutes": {
        "en": "min",
        "hi": "मि",
        "mr": "मिनिटे",
        "ta": "நிமிடங்கள்",
        "te": "నిమి",
        "bn": "মিনিট",
        "ml": "മിനിറ്റ്",
    },
    "disclaimer": {
        "en": "ORCA is a decision-support tool. It does not replace official marine advisories or Coast Guard instructions.",
        "hi": "ORCA एक निर्णय-सहायक उपकरण है। यह आधिकारिक समुद्री सलाह या तटरक्षक निर्देशों का विकल्प नहीं है।",
        "mr": "ORCA हे निर्णय-सहाय्य साधन आहे. ते अधिकृत सागरी सल्ला किंवा तटरक्षक दलाच्या सूचनांना पर्याय नाही.",
        "ta": "ORCA என்பது முடிவெடுக்கும் ஆதரவு கருவி மட்டுமே. இது அதிகாரப்பூர்வ கடல் எச்சரிக்கைகளுக்கு மாற்றாகாது.",
        "te": "ORCA ఒక నిర్ణయ మద్దతు సాధనం. ఇది అధికారిక సముద్ర హెచ్చరికలకు ప్రత్యామ్నాయం కాదు.",
        "bn": "ORCA একটি সিদ্ধান্ত সহায়তা ব্যবস্থা। এটি সরকারি সতর্কবার্তার বিকল্প নয়।",
        "ml": "ORCA ഒരു തീരുമാന പിന്തുണ സംവിധാനമാണ്. ഇത് ഔദ്യോഗിക സമുദ്ര മുന്നറിയിപ്പുകൾക്ക് പകരമല്ല.",
    },
}

SUGGESTIONS: Dict[str, List[str]] = {
    "en": ["What about 12 PM?", "Show nearby fishing zones", "Give me the safest route", "Is there a cyclone nearby?"],
    "hi": ["दोपहर 12 बजे कैसा रहेगा?", "पास के मत्स्य क्षेत्र दिखाओ", "सबसे सुरक्षित रास्ता बताओ", "क्या आसपास कोई चक्रवात है?"],
    "mr": ["दुपारी १२ वाजता काय?", "जवळचे PFZ दाखवा", "सुरक्षित मार्ग दाखवा", "जवळपास चक्रीवादळ आहे का?"],
    "ta": ["மதியம் 12 மணிக்கு எப்படி?", "அருகிலுள்ள மீன்பிடி பகுதிகளைக் காட்டு", "பாதுகாப்பான பாதையைக் காட்டு", "புயல் எச்சரிக்கை உள்ளதா?"],
    "te": ["మధ్యాహ్నం 12 గంటలకు ఎలా ఉంటుంది?", "సమీపంలోని PFZ చూపించు", "సురక్షితమైన మార్గాన్ని చూపించు", "తుఫాను ఉందా?"],
    "bn": ["দুপুর ১২টায় কেমন থাকবে?", "কাছের মাছ ধরার অঞ্চল দেখাও", "নিরাপদ পথ দেখাও", "কাছাকাছি কি ঘূর্ণিঝড় আছে?"],
    "ml": ["ഉച്ചയ്ക്ക് 12 മണിക്ക് എങ്ങനെ?", "അടുത്തുള്ള PFZ കാണിക്കുക", "ഏറ്റവും സുരക്ഷിതമായ വഴി കാണിക്കുക", "ചുഴലിക്കാറ്റ് മുന്നറിയിപ്പ് ഉണ്ടോ?"],
}


def t(key: str, lang: str, **kwargs) -> str:
    template = T.get(key, {}).get(lang) or T.get(key, {}).get("en", key)
    return template.format(**kwargs) if kwargs else template


def verdict_key(category: str) -> str:
    return {"LOW": "verdict_low", "MODERATE": "verdict_moderate",
            "HIGH": "verdict_high", "EXTREME": "verdict_extreme"}[category]


def humanise_duration(minutes: int, lang: str) -> str:
    h, m = divmod(int(minutes), 60)
    if h and m:
        return f"{h} {t('hours', lang)} {m} {t('minutes', lang)}"
    if h:
        return f"{h} {t('hours', lang)}"
    return f"{m} {t('minutes', lang)}"
