import os
from typing import Optional

# Comprehensive local dictionary translations for core stadium terms across 13 Indian languages
LOCAL_TRANSLATIONS = {
    "en": {
        "title": "ArenaFlow Advanced Panel",
        "lbl_match": "Today's Match",
        "lbl_capacity": "Stadium Capacity",
        "lbl_seats_booked": "Seats Booked",
        "lbl_seats_avail": "Seats Available",
        "lbl_gate_status": "Gate Status",
        "lbl_restrooms": "Restroom Locations",
        "lbl_medical": "Medical Centers",
        "lbl_parking": "Smart Parking",
        "lbl_merch": "Merchandise Shop",
        "lbl_exits": "Emergency Exits",
        "lbl_weather": "Weather Conditions",
        "lbl_predictions": "Crowd Predictions",
        "lbl_voice_btn": "Hold to Speak",
        "lbl_assistant_title": "AI Stadium Super Assistant",
    },
    "hi": {  # Hindi
        "title": "एरिनाफ्लो उन्नत पैनल",
        "lbl_match": "आज का मैच",
        "lbl_capacity": "स्टेडियम की क्षमता",
        "lbl_seats_booked": "आरक्षित सीटें",
        "lbl_seats_avail": "उपलब्ध सीटें",
        "lbl_gate_status": "गेट की स्थिति",
        "lbl_restrooms": "शौचालय के स्थान",
        "lbl_medical": "चिकित्सा केंद्र",
        "lbl_parking": "स्मार्ट पार्किंग",
        "lbl_merch": "मर्चेंडाइज दुकान",
        "lbl_exits": "आपातकालीन निकास",
        "lbl_weather": "मौसम की स्थिति",
        "lbl_predictions": "भीड़ का पूर्वानुमान",
        "lbl_voice_btn": "बोलने के लिए दबाएं",
        "lbl_assistant_title": "एआई स्टेडियम सुपर सहायक",
    },
    "kn": {  # Kannada
        "title": "ಅರೆನಾಫ್ಲೋ ಸುಧಾರಿತ ಫಲಕ",
        "lbl_match": "ಇಂದಿನ ಪಂದ್ಯ",
        "lbl_capacity": "ಕ್ರೀಡಾಂಗಣದ ಸಾಮರ್ಥ್ಯ",
        "lbl_seats_booked": "ಕಾಯ್ದಿರಿಸಿದ ಆಸನಗಳು",
        "lbl_seats_avail": "ಲಭ್ಯವಿರುವ ಆಸನಗಳು",
        "lbl_gate_status": "ಗೇಟ್ ಸ್ಥಿತಿ",
        "lbl_restrooms": "ಶೌಚಾಲಯದ ಸ್ಥಳಗಳು",
        "lbl_medical": "ವೈದ್ಯಕೀಯ ಕೇಂದ್ರಗಳು",
        "lbl_parking": "ಸ್ಮಾರ್ಟ್ ಪಾರ್ಕಿಂಗ್",
        "lbl_merch": "ಸಾಮಗ್ರಿಗಳ ಅಂಗಡಿ",
        "lbl_exits": "ತುರ್ತು ನಿರ್ಗಮನಗಳು",
        "lbl_weather": "ಹವಾಮಾನ ಸ್ಥಿತಿ",
        "lbl_predictions": "ಜನಸಂದಣಿ ಮುನ್ಸೂಚನೆಗಳು",
        "lbl_voice_btn": "ಮಾತನಾಡಲು ಒತ್ತಿಹಿಡಿಯಿರಿ",
        "lbl_assistant_title": "ಎಐ ಕ್ರೀಡಾಂಗಣ ಸೂಪರ್ ಸಹಾಯಕ",
    },
    "ta": {  # Tamil
        "title": "அரினாஃப்ளோ மேம்பட்ட குழு",
        "lbl_match": "இன்றைய போட்டி",
        "lbl_capacity": "அரங்கத்தின் கொள்ளளவு",
        "lbl_seats_booked": "பதிவு செய்யப்பட்ட இடங்கள்",
        "lbl_seats_avail": "கிடைக்கக்கூடிய இடங்கள்",
        "lbl_gate_status": "வாயில் நிலை",
        "lbl_restrooms": "கழிப்பறை இடங்கள்",
        "lbl_medical": "மருத்துவ மையங்கள்",
        "lbl_parking": "ஸ்மார்ட் பார்க்கிங்",
        "lbl_merch": "வணிகக் கடை",
        "lbl_exits": "அவசரகால வழிகள்",
        "lbl_weather": "வானிலை நிலவரம்",
        "lbl_predictions": "கூட்ட கணிப்புகள்",
        "lbl_voice_btn": "பேச அழுத்திப் பிடிக்கவும்",
        "lbl_assistant_title": "AI அரங்கம் சூப்பர் உதவியாளர்",
    },
    "te": {  # Telugu
        "title": "అరేనాఫ్లో అడ్వాన్స్డ్ ప్యానెల్",
        "lbl_match": "నేటి మ్యాచ్",
        "lbl_capacity": "స్టేడియం సామర్థ్యం",
        "lbl_seats_booked": "బుక్ చేసిన సీట్లు",
        "lbl_seats_avail": "అందుబాటులో ఉన్న సీట్లు",
        "lbl_gate_status": "గేట్ స్థితి",
        "lbl_restrooms": "శౌచాలయాల స్థానాలు",
        "lbl_medical": "వైద్య కేంద్రాలు",
        "lbl_parking": "స్మార్ట్ పార్కింగ్",
        "lbl_merch": "మర్చండైజ్ దుకాణం",
        "lbl_exits": "అవసర నిష్క్రమణలు",
        "lbl_weather": "వాతావరణ పరిస్థితులు",
        "lbl_predictions": "జనసమూహ అంచనాలు",
        "lbl_voice_btn": "మాట్లాడటానికి నొక్కండి",
        "lbl_assistant_title": "AI స్టేడియం సూపర్ అసిస్టెంట్",
    },
    "ml": {  # Malayalam
        "title": "അരീനഫ്ലോ അഡ്വാൻസ്ഡ് പാനൽ",
        "lbl_match": "ഇന്നത്തെ മത്സരം",
        "lbl_capacity": "സ്റ്റേഡിയം ശേഷി",
        "lbl_seats_booked": "ബുക്ക് ചെയ്ത സീറ്റുകൾ",
        "lbl_seats_avail": "ലഭ്യമായ സീറ്റുകൾ",
        "lbl_gate_status": "ഗേറ്റ് നില",
        "lbl_restrooms": "ശൗചാലയ സ്ഥാനങ്ങൾ",
        "lbl_medical": "മെഡിക്കൽ കേന്ദ്രങ്ങൾ",
        "lbl_parking": "സ്മാർട്ട് പാർക്കിംഗ്",
        "lbl_merch": "വ്യാപാര ശാല",
        "lbl_exits": "അടിയന്തിര എക്സിറ്റുകൾ",
        "lbl_weather": "കാലാവസ്ഥാ വിവരങ്ങൾ",
        "lbl_predictions": "ജനക്കൂട്ട പ്രവചനങ്ങൾ",
        "lbl_voice_btn": "സംസാരിക്കാൻ അമർത്തുക",
        "lbl_assistant_title": "AI സ്റ്റേഡിയം സൂപ്പർ അസിസ്റ്റന്റ്",
    },
    "mr": {  # Marathi
        "title": "अ‍ॅरेनाफ्लो प्रगत पॅनेल",
        "lbl_match": "आजचा सामना",
        "lbl_capacity": "स्टेडियमची क्षमता",
        "lbl_seats_booked": "आरक्षित जागा",
        "lbl_seats_avail": "उपलब्ध जागा",
        "lbl_gate_status": "गेटची स्थिती",
        "lbl_restrooms": "शौचालयाची ठिकाणे",
        "lbl_medical": "वैद्यकीय केंद्रे",
        "lbl_parking": "स्मार्ट पार्किंग",
        "lbl_merch": "मर्चेंडाईज दुकान",
        "lbl_exits": "आणीबाणीचे निकास",
        "lbl_weather": "हवामानाची स्थिती",
        "lbl_predictions": "गर्दीचा अंदाज",
        "lbl_voice_btn": "बोलण्यासाठी दाबा",
        "lbl_assistant_title": "एआय स्टेडियम सुपर असिस्टंट",
    },
    "gu": {  # Gujarati
        "title": "એરેનાફ્લો એડવાન્સ પેનલ",
        "lbl_match": "આજની મેચ",
        "lbl_capacity": "સ્ટેડિયમની ક્ષમતા",
        "lbl_seats_booked": "બુક કરેલી બેઠકો",
        "lbl_seats_avail": "ઉપલબ્ધ બેઠકો",
        "lbl_gate_status": "ગેટની સ્થિતિ",
        "lbl_restrooms": "શૌચાલયોના સ્થાનો",
        "lbl_medical": "મેડિકલ સેન્ટરો",
        "lbl_parking": "સ્માર્ટ પાર્કિંગ",
        "lbl_merch": "મર્ચેન્ડાઇઝ દુકાન",
        "lbl_exits": "ઇમરજન્સી એક્ઝિટ",
        "lbl_weather": "હવામાનની સ્થિતિ",
        "lbl_predictions": "ભીડનું પૂર્વાનુમાન",
        "lbl_voice_btn": "બોલવા માટે દબાવી રાખો",
        "lbl_assistant_title": "એઆઈ સ્ટેડિયમ સુપર આસિસ્ટન્ટ",
    },
    "pa": {  # Punjabi
        "title": "ਐਰੇਨਾਫਲੋ ਐਡਵਾਂਸਡ ਪੈਨਲ",
        "lbl_match": "ਅੱਜ ਦਾ ਮੈਚ",
        "lbl_capacity": "ਸਟੇਡੀਅਮ ਦੀ ਸਮਰੱਥਾ",
        "lbl_seats_booked": "ਬੁੱਕ ਕੀਤੀਆਂ ਸੀਟਾਂ",
        "lbl_seats_avail": "ਉਪਲਬਧ ਸੀਟਾਂ",
        "lbl_gate_status": "ਗੇਟ ਦੀ ਸਥਿਤੀ",
        "lbl_restrooms": "ਸ਼ੌਚਾਲਿਆ ਦੇ ਸਥਾਨ",
        "lbl_medical": "ਮੈਡੀਕਲ ਸੈਂਟਰ",
        "lbl_parking": "ਸਮਾਰਟ ਪਾਰਕਿੰਗ",
        "lbl_merch": "ਮਰਚੈਂਡਾਈਜ਼ ਦੁਕਾਨ",
        "lbl_exits": "ਐਮਰਜੈਂਸੀ ਨਿਕਾਸ",
        "lbl_weather": "ਮੌਸਮ ਦੀ ਸਥਿਤੀ",
        "lbl_predictions": "ਭੀੜ ਦਾ ਪੂਰਵਅਨੁਮਾਨ",
        "lbl_voice_btn": "ਬੋਲਣ ਲਈ ਦਬਾਓ",
        "lbl_assistant_title": "ਏਆਈ ਸਟੇਡੀਅਮ ਸੁਪਰ ਸਹਾਇਕ",
    },
    "bn": {  # Bengali
        "title": "অ্যারেনাফ্লো অ্যাডভান্সড প্যানেল",
        "lbl_match": "আজকের ম্যাচ",
        "lbl_capacity": "স্টেডিয়ামের ক্ষমতা",
        "lbl_seats_booked": "বুক করা আসন",
        "lbl_seats_avail": "উপলব্ধ আসন",
        "lbl_gate_status": "গেট স্ট্যাটাস",
        "lbl_restrooms": "টয়লেটের অবস্থান",
        "lbl_medical": "মেডিকেল সেন্টার",
        "lbl_parking": "স্মার্ট পার্কিং",
        "lbl_merch": "মার্চেন্ডাইজ শপ",
        "lbl_exits": "জরুরী প্রস্থান",
        "lbl_weather": "আবহাওয়া পরিস্থিতি",
        "lbl_predictions": "ভিড়ের পূর্বাভাস",
        "lbl_voice_btn": "বলার জন্য টিপুন",
        "lbl_assistant_title": "এআই স্টেডিয়াম সুপার অ্যাসিস্ট্যান্ট",
    },
    "ur": {  # Urdu
        "title": "ایرینا فلو ایڈوانسڈ پینل",
        "lbl_match": "آج کا میچ",
        "lbl_capacity": "اسٹیڈیم کی گنجائش",
        "lbl_seats_booked": "بک شدہ نشستیں",
        "lbl_seats_avail": "دستیاب نشستیں",
        "lbl_gate_status": "گیٹ کی صورتحال",
        "lbl_restrooms": "بیت الخلاء کے مقامات",
        "lbl_medical": "طبی مراکز",
        "lbl_parking": "اسمارٹ پارکنگ",
        "lbl_merch": "سامان کی دکان",
        "lbl_exits": "ہنگامی اخراج",
        "lbl_weather": "موسم کی صورتحال",
        "lbl_predictions": "ہجوم کی پیش گوئی",
        "lbl_voice_btn": "بولنے کے لیے دبائیں",
        "lbl_assistant_title": "اے آئی اسٹیڈیم سپر اسسٹنٹ",
    },
    "or": {  # Odia
        "title": "ଆରେନାଫ୍ଲୋ ଆଡଭାନ୍ସ ପ୍ୟାନେଲ",
        "lbl_match": "ଆଜିର ମ୍ୟାଚ୍",
        "lbl_capacity": "ଷ୍ଟାଡିୟମ୍ କ୍ଷମତା",
        "lbl_seats_booked": "ବୁକ୍ ହୋଇଥିବା ସିଟ୍",
        "lbl_seats_avail": "ଉପଲବ୍ଧ ସିଟ୍",
        "lbl_gate_status": "ଗେଟ୍ ସ୍ଥିତି",
        "lbl_restrooms": "ଶୌଚାଳୟ ସ୍ଥାନ",
        "lbl_medical": "ଚିକିତ୍ସା କେନ୍ଦ୍ର",
        "lbl_parking": "ସ୍ମାର୍ଟ ପାର୍କିଂ",
        "lbl_merch": "ମର୍ଚାଣ୍ଡାଇଜ୍ ଦୋକାନ",
        "lbl_exits": "ଜରୁରୀକାଳୀନ ପ୍ରସ୍ଥାନ",
        "lbl_weather": "ପାଣିପାଗ ସୂଚନା",
        "lbl_predictions": "ଭିଡ଼ ପୂର୍ବାନୁମାନ",
        "lbl_voice_btn": "କହିବା ପାଇଁ ଦବାନ୍ତୁ",
        "lbl_assistant_title": "AI ଷ୍ଟାଡିୟମ ସୁପର ସହାୟକ",
    },
    "kok": {  # Konkani
        "title": "अरेनाफ्लो प्रगत पॅनेल",
        "lbl_match": "आजची मॅच",
        "lbl_capacity": "स्टेडियमची क्षमता",
        "lbl_seats_booked": "बुक केल्ल्यो सीटी",
        "lbl_seats_avail": "मेळपी सीटी",
        "lbl_gate_status": "गेटाची स्थिती",
        "lbl_restrooms": "संडासाची सुवात",
        "lbl_medical": "वैजकी केंद्र",
        "lbl_parking": "स्मार्ट पार्किंग",
        "lbl_merch": "मर्चेंडायझ दुकान",
        "lbl_exits": "इमर्जन्सी वाटा",
        "lbl_weather": "हवामानाची स्थिती",
        "lbl_predictions": "गर्दीचो अंदाज",
        "lbl_voice_btn": "उलोवपाक दाबून दवरात",
        "lbl_assistant_title": "एआय स्टेडियम सुपर सहाय्यक",
    },
}


class TranslationService:
    """Service class responsible for translating UI strings across local dictionaries.

    Attributes:
        api_key (Optional[str]): Key for Google Translation API if configured.
    """

    def __init__(self) -> None:
        """Initializes TranslationService and checks configuration."""
        self.api_key: Optional[str] = os.environ.get("GOOGLE_TRANSLATION_API_KEY")

    def translate_key(self, key: str, target_lang: str) -> str:
        """Translates a specific key to a target language fallback dictionary.

        Args:
            key (str): UI dictionary identifier key.
            target_lang (str): Language code (e.g. en, hi, kn).

        Returns:
            str: Translated text string.
        """
        target = str(target_lang).lower()
        if target not in LOCAL_TRANSLATIONS:
            target = "en"

        lang_dict = LOCAL_TRANSLATIONS.get(target, LOCAL_TRANSLATIONS["en"])
        return lang_dict.get(key, LOCAL_TRANSLATIONS["en"].get(key, key))

    def translate_text(self, text: str, target_lang: str) -> str:
        """Translates an arbitrary string via standard translation models.

        Args:
            text (str): Source text body.
            target_lang (str): Target language code.

        Returns:
            str: Translated string.
        """
        # Local fallback does nothing, just returns text.
        return text
