# bio_seed_data.py
# ==========================================================================
#  BIOLOGIYA O'YINI — NAMUNA BAZA
# ==========================================================================
# Admin panelidagi "Namuna terminlarni yuklash" tugmasi shu ma'lumotni
# bazaga qo'shadi.
#
# TERMIN maydonlari tartibi:
#   (termin, ta'rifi, vazifasi, guruhi, ipuchalar, qiziqarli fakt)
#
#   - "guruhi"    -> GURUHLASH o'yinida savat nomi bo'ladi
#   - "ipuchalar" -> "KIM MEN?" o'yinida ketma-ket ochiladi.
#                    UMUMIYDAN ANIQQA tartibda yozilgan: birinchi ipucha
#                    javobni oshkor qilmasligi kerak, oxirgisi esa deyarli
#                    aniq ko'rsatishi kerak.
#   - Bo'sh maydon None qilib qoldirilgan — generator bo'sh maydondan
#     savol yasamaydi, shuning uchun "javobi yo'q" savol chiqmaydi.
#
# KETMA-KETLIK bosqichlari TO'G'RI TARTIBDA yoziladi; o'quvchiga
# aralashtirilgan holda ko'rsatiladi.

# ==========================================================================
#  1. HUJAYRA VA ORGANOIDLAR
# ==========================================================================

_HUJAYRA = [
    {
        "title": "Hujayra organoidlari",
        "terms": [
            ("Yadro", "Irsiy axborot saqlanadigan boshqaruv markazi",
             "DNK ni saqlaydi va hujayra faoliyatini boshqaradi", "Eukariot",
             ["Menda qo'sh membrana bor", "Ichimda yadrocha joylashgan",
              "Men irsiy axborotni saqlayman"],
             "Prokariotlarda men yo'q — u yerda nukleoid bo'ladi"),

            ("Mitoxondriya", "Hujayraning energiya stansiyasi",
             "Nafas olish orqali ATP sintez qiladi", "Eukariot",
             ["Menda ikki qavatli membrana bor", "Ichki membranam kristalar hosil qiladi",
              "Men ATP ishlab chiqaraman"],
             "O'z DNK si va ribosomalariga ega"),

            ("Ribosoma", "Oqsil sintezi boradigan membranasiz zarracha",
             "Aminokislotalardan oqsil yig'adi", "Umumiy",
             ["Menda membrana umuman yo'q", "Men ikki subbirlikdan iboratman",
              "Men oqsil yig'aman"],
             "Prokariotda 70S, eukariotda 80S"),

            ("Endoplazmatik to'r", "Naycha va bo'shliqlardan iborat ichki tarmoq",
             "Moddalarni sintez qiladi va tashiydi", "Eukariot",
             ["Men naychalar tarmog'iman", "Donador shaklimda ribosomalar joylashadi"],
             "Donador (oqsil) va silliq (yog', uglevod) turlari bor"),

            ("Golji majmuasi", "Yassi xaltachalar to'plami",
             "Moddalarni saralaydi, qadoqlaydi va chiqaradi", "Eukariot",
             ["Men yassi xaltachalardan iboratman", "Men moddalarni qadoqlab jo'nataman"],
             "Lizosomalarni hosil qiladi"),

            ("Lizosoma", "Hazm fermentlari bilan to'la pufakcha",
             "Hujayra ichida moddalarni hazm qiladi", "Eukariot",
             ["Ichimda gidrolitik fermentlar bor", "Men keraksiz qismlarni parchalayman"],
             "\"Hujayra oshqozoni\" deb ataladi"),

            ("Xloroplast", "Xlorofill saqlovchi yashil plastida",
             "Fotosintez orqali organik modda hosil qiladi", "O'simlik",
             ["Menda yashil pigment bor", "Men yorug'lik energiyasini o'zlashtiraman"],
             "O'z DNK siga ega, mitoxondriyaga o'xshab"),

            ("Vakuola", "Hujayra shirasi bilan to'lgan bo'shliq",
             "Suv va moddalarni saqlaydi, turgorni ushlab turadi", "O'simlik",
             ["Men o'simlik hujayrasining katta qismini egallayman"],
             "Yosh hujayrada kichik, yetuk hujayrada juda katta"),

            ("Hujayra devori", "Sellulozadan iborat qattiq tashqi qobiq",
             "Hujayraga shakl beradi va himoya qiladi", "O'simlik",
             ["Men sellulozadan tuzilganman", "Men hujayraga qat'iy shakl beraman"],
             "Zamburug'larda xitindan, bakteriyalarda murein­dan iborat"),

            ("Hujayra membranasi", "Ikki qavat lipid va oqsillardan iborat parda",
             "Moddalarning kirib-chiqishini tanlab boshqaradi", "Umumiy",
             ["Men ikki qavat lipiddan iboratman", "Men moddalarni tanlab o'tkazaman"],
             "Suyuq mozaika modeli bilan tushuntiriladi"),

            ("Sitoplazma", "Hujayraning yarim suyuq ichki muhiti",
             "Organoidlarni joylashtiradi, moddalar almashinuvi shu yerda boradi", "Umumiy",
             None, None),

            ("Sentriola", "Ikkita silindrsimon tanachadan iborat hujayra markazi",
             "Bo'linishda urchuq iplarini hosil qiladi", "Hayvon",
             ["Men bo'linish paytida ip tortaman"],
             "Yuksak o'simliklarda uchramaydi"),
        ],
        "sequences": [
            {
                "title": "Oqsilning hujayra ichidagi yo'li",
                "description": "Sintez qilingan oqsil qayerdan qayerga boradi?",
                "steps": [
                    "Yadroda DNK dan i-RNK ko'chiriladi",
                    "i-RNK yadrodan sitoplazmaga chiqadi",
                    "Ribosomada oqsil yig'iladi",
                    "Oqsil donador endoplazmatik to'rga o'tadi",
                    "Golji majmuasida saralanadi va qadoqlanadi",
                    "Pufakcha bilan hujayradan chiqariladi",
                ],
            },
        ],
    },
    {
        "title": "Prokariot va eukariot",
        "terms": [
            ("Nukleoid", "Bakteriyaning halqasimon DNK si joylashgan soha",
             "Irsiy axborotni saqlaydi", "Prokariot",
             ["Menda membrana yo'q", "Men halqasimon DNK dan iboratman"],
             "Yadrodan farqli — membrana bilan o'ralmagan"),
            ("Mezosoma", "Membrananing ichkariga botgan burmasi",
             "Nafas olish fermentlarini joylashtiradi", "Prokariot", None,
             "Mitoxondriya vazifasini qisman bajaradi"),
            ("Kapsula", "Bakteriya ustidagi shilimshiq qavat",
             "Quruqlik va fagotsitozdan himoya qiladi", "Prokariot", None, None),
            ("Plazmida", "Asosiy DNK dan tashqaridagi kichik halqasimon DNK",
             "Qo'shimcha belgilarni (masalan antibiotikka chidamlilikni) tashiydi",
             "Prokariot", None, "Gen injeneriyasida vektor sifatida ishlatiladi"),
            ("Xivchin", "Harakat organoidi",
             "Hujayraning harakatlanishini ta'minlaydi", "Prokariot", None, None),
            ("Yadrocha", "Yadro ichidagi zich tanacha",
             "Ribosoma qismlarini hosil qiladi", "Eukariot", None, None),
            ("Xromosoma", "Oqsil bilan o'ralgan chiziqsimon DNK",
             "Irsiy axborotni tashiydi va bo'linishda taqsimlaydi", "Eukariot",
             ["Men bo'linish paytida yaqqol ko'rinaman"], None),
            ("Plastidalar", "O'simlik hujayrasining rangli organoidlari",
             "Fotosintez va zahira moddalarni saqlash", "Eukariot", None,
             "Xloroplast, xromoplast va leykoplast turlari bor"),
        ],
    },
]


# ==========================================================================
#  2. ODAM ORGAN TIZIMLARI
# ==========================================================================

_ORGAN_TIZIMLARI = [
    {
        "title": "Hazm tizimi",
        "terms": [
            ("Og'iz bo'shlig'i", "Hazm yo'lining boshlanish qismi",
             "Ovqatni mexanik maydalaydi, so'lak amilazasi kraxmalni parchalaydi",
             "Hazm yo'li", ["Menda hazm so'lak fermenti bilan boshlanadi"], None),
            ("Qizilo'ngach", "Halqumni oshqozon bilan bog'lovchi naysimon organ",
             "Ovqatni to'lqinsimon harakat bilan oshqozonga o'tkazadi", "Hazm yo'li",
             None, "Peristaltika tufayli boshi pastga qaragan holda ham ishlaydi"),
            ("Oshqozon", "Ovqat vaqtincha saqlanadigan mushakli xalta",
             "Pepsin va xlorid kislota yordamida oqsilni parchalaydi", "Hazm yo'li",
             ["Menda kislotali muhit bor", "Men oqsilni parchalayman"],
             "Shilliq qavat o'zini kislotadan himoya qiladi"),
            ("O'n ikki barmoq ichak", "Ingichka ichakning birinchi qismi",
             "Jigar o'ti va me'da osti bezi shirasi shu yerga quyiladi", "Hazm yo'li",
             None, None),
            ("Ingichka ichak", "Hazm yo'lining eng uzun qismi",
             "Ovqat hazmini yakunlaydi va moddalarni qonga so'radi", "Hazm yo'li",
             ["Ichki yuzamda vorsinkalar bor", "Men so'rilishning asosiy joyiman"],
             "Vorsinkalar tufayli yuzasi ~200 m² ga yetadi"),
            ("Yo'g'on ichak", "Hazm yo'lining oxirgi qismi",
             "Suvni so'radi, bakteriyalar K va B vitaminlarini sintez qiladi",
             "Hazm yo'li", None, None),
            ("Jigar", "Organizmning eng yirik bezi",
             "O't ishlab chiqaradi, zaharli moddalarni zararsizlantiradi", "Hazm bezi",
             ["Men o't suyuqligini ishlab chiqaraman", "Men qonni zaharlardan tozalayman"],
             "Glikogen shaklida uglevod zahirasini saqlaydi"),
            ("Me'da osti bezi", "Aralash sekretsiyali bez",
             "Hazm fermentlarini va insulin gormonini ishlab chiqaradi", "Hazm bezi",
             ["Men ham ferment, ham gormon ishlab chiqaraman"],
             "Insulin yetishmasa qandli diabet rivojlanadi"),
            ("So'lak bezi", "Og'iz bo'shlig'iga ochiluvchi bez",
             "So'lak ajratadi, tarkibidagi amilaza kraxmalni parchalaydi", "Hazm bezi",
             None, None),
        ],
        "sequences": [
            {
                "title": "Ovqatning hazm yo'lidagi harakati",
                "description": "Ovqat qaysi organlardan ketma-ket o'tadi?",
                "steps": ["Og'iz bo'shlig'i", "Halqum", "Qizilo'ngach", "Oshqozon",
                          "O'n ikki barmoq ichak", "Ingichka ichak", "Yo'g'on ichak",
                          "To'g'ri ichak"],
            },
        ],
    },
    {
        "title": "Qon aylanish va nafas",
        "terms": [
            ("Yurak", "To'rt kamerali mushakli nasos",
             "Qonni tomirlar bo'ylab haydaydi", "Qon aylanish",
             ["Menda to'rtta kamera bor", "Men to'xtovsiz ishlayman"],
             "Kuniga ~100 000 marta uradi"),
            ("Arteriya", "Yurakdan qon olib ketuvchi tomir",
             "Qonni organlarga yetkazadi", "Qon aylanish",
             ["Mening devorim qalin va elastik", "Men yurakdan boshlanaman"], None),
            ("Vena", "Yurakka qon olib keluvchi tomir",
             "Qonni organlardan yurakka qaytaradi", "Qon aylanish",
             ["Menda qonning orqaga qaytishiga to'sqinlik qiluvchi klapanlar bor"], None),
            ("Kapillyar", "Eng ingichka qon tomiri",
             "Qon bilan to'qima orasida modda va gaz almashinuvini ta'minlaydi",
             "Qon aylanish", ["Mening devorim bir qavat hujayradan iborat"],
             "Diametri eritrotsitdan sal kattaroq"),
            ("Eritrotsit", "Yadrosiz qizil qon tanachasi",
             "Gemoglobin yordamida kislorod tashiydi", "Qon",
             ["Menda yadro yo'q", "Menda temir saqlovchi pigment bor"],
             "Umri ~120 kun"),
            ("Leykotsit", "Oq qon tanachasi",
             "Organizmni mikroblardan himoya qiladi", "Qon",
             ["Men shaklimni o'zgartira olaman", "Men mikroblarni yutaman"], None),
            ("Trombotsit", "Qon plastinkasi",
             "Qonning ivishida qatnashadi", "Qon", None, None),
            ("O'pka", "Nafas olishning asosiy organi",
             "Havo bilan qon orasida gaz almashinuvini ta'minlaydi", "Nafas",
             ["Men ko'krak qafasida joylashganman", "Menda millionlab pufakchalar bor"], None),
            ("Alveola", "O'pkadagi mayda havo pufakchasi",
             "Kislorod va karbonat angidrid almashinuvi shu yerda boradi", "Nafas",
             ["Men juda mayda pufakchaman", "Atrofimni kapillyarlar o'rab olgan"],
             "Umumiy yuzasi ~100 m²"),
            ("Traxeya", "Halqumdan bronxlarga boruvchi havo yo'li",
             "Havoni o'pkaga o'tkazadi", "Nafas", None,
             "Tog'ay halqalari tufayli yopilib qolmaydi"),
            ("Bronx", "Traxeyaning ikkiga ajralgan tarmog'i",
             "Havoni o'pkaning ichiga tarqatadi", "Nafas", None, None),
            ("Diafragma", "Ko'krak va qorin bo'shlig'ini ajratuvchi mushak",
             "Qisqarib nafas olishni ta'minlaydi", "Nafas",
             ["Men gumbazsimon mushakman", "Men qisqarsam havo ichkariga kiradi"], None),
        ],
        "sequences": [
            {
                "title": "Kichik (o'pka) qon aylanish doirasi",
                "description": "Qon qayerdan boshlab qayerga qaytadi?",
                "steps": ["O'ng qorincha", "O'pka arteriyasi", "O'pka kapillyarlari",
                          "O'pka venasi", "Chap bo'lmacha"],
            },
            {
                "title": "Katta (tana) qon aylanish doirasi",
                "description": "Kislorodga boy qon tanaga qanday tarqaladi?",
                "steps": ["Chap qorincha", "Aorta", "Arteriyalar", "Tana kapillyarlari",
                          "Venalar", "Kovak venalar", "O'ng bo'lmacha"],
            },
        ],
    },
]


# ==========================================================================
#  3. GENETIKA VA BO'LINISH
# ==========================================================================

_GENETIKA = [
    {
        "title": "Hujayra bo'linishi",
        "terms": [
            ("Interfaza", "Bo'linishlar orasidagi tayyorgarlik davri",
             "DNK ikki hissa ortadi, hujayra o'sadi", "Bo'linish davri",
             ["Bu davrda DNK ikki hissa ortadi"], "Hujayra umrining ~90% ini egallaydi"),
            ("Profaza", "Bo'linishning birinchi bosqichi",
             "Xromosomalar spirallashadi, yadro pardasi yo'qoladi", "Mitoz bosqichi",
             ["Bu bosqichda yadro pardasi yo'qoladi"], None),
            ("Metafaza", "Bo'linishning ikkinchi bosqichi",
             "Xromosomalar ekvator tekisligiga joylashadi", "Mitoz bosqichi",
             ["Bu bosqichda xromosomalar bir qatorga tiziladi"],
             "Xromosomalarni sanash uchun eng qulay bosqich"),
            ("Anafaza", "Bo'linishning uchinchi bosqichi",
             "Xromatidalar qutblarga tortiladi", "Mitoz bosqichi",
             ["Bu bosqichda xromatidalar ajralib, qarama-qarshi tomonga ketadi"], None),
            ("Telofaza", "Bo'linishning oxirgi bosqichi",
             "Yadro pardasi tiklanadi, sitoplazma bo'linadi", "Mitoz bosqichi",
             ["Bu bosqichda ikkita yangi yadro paydo bo'ladi"], None),
            ("Mitoz", "Tana hujayralarining bo'linish usuli",
             "Onaliknikiga teng xromosomali ikkita hujayra hosil qiladi", "Bo'linish turi",
             ["Mendan ikkita bir xil hujayra hosil bo'ladi"], "2n → 2n + 2n"),
            ("Meyoz", "Jinsiy hujayralar hosil bo'lish usuli",
             "Xromosomalar sonini ikki barobar kamaytiradi", "Bo'linish turi",
             ["Mendan to'rtta hujayra hosil bo'ladi", "Mendan keyin xromosoma soni yarmiga tushadi"],
             "2n → n + n + n + n"),
            ("Krossingover", "Gomologik xromosomalar orasidagi uchastka almashinuvi",
             "Irsiy o'zgaruvchanlikni oshiradi", "Bo'linish hodisasi",
             ["Men meyozning profaza I bosqichida sodir bo'laman"], None),
            ("Xromatida", "Xromosomaning bo'ylama yarmi",
             "Bo'linishda qutblarga taqsimlanadi", "Tuzilma", None, None),
            ("Sentromera", "Xromosomaning belbog' qismi",
             "Xromatidalarni birlashtiradi, urchuq ipi shu yerga birikadi", "Tuzilma",
             None, None),
        ],
        "sequences": [
            {
                "title": "Mitoz bosqichlari",
                "description": "Tana hujayrasi qanday tartibda bo'linadi?",
                "steps": ["Interfaza", "Profaza", "Metafaza", "Anafaza", "Telofaza"],
            },
            {
                "title": "Meyoz I bosqichlari",
                "description": "Birinchi meyotik bo'linish tartibi",
                "steps": ["Profaza I", "Metafaza I", "Anafaza I", "Telofaza I"],
            },
        ],
    },
    {
        "title": "DNK va oqsil sintezi",
        "terms": [
            ("DNK", "Ikki zanjirli spiral shaklidagi nuklein kislota",
             "Irsiy axborotni saqlaydi va avlodga uzatadi", "Nuklein kislota",
             ["Men ikki zanjirdan iboratman", "Mening zanjirlarim spiral shaklda buralgan"],
             "Uotson va Krik 1953-yilda tuzilishini aniqlagan"),
            ("i-RNK", "Axborot RNK si",
             "DNK dagi axborotni ribosomaga olib boradi", "Nuklein kislota",
             ["Men yadrodan sitoplazmaga axborot olib chiqaman"], "mRNK deb ham ataladi"),
            ("t-RNK", "Tashuvchi RNK",
             "Aminokislotalarni ribosomaga olib keladi", "Nuklein kislota",
             ["Men beda bargiga o'xshab buralganman", "Men aminokislota tashiyman"], None),
            ("r-RNK", "Ribosoma RNK si",
             "Ribosomaning tarkibiy qismini tashkil qiladi", "Nuklein kislota", None, None),
            ("Nukleotid", "Nuklein kislotaning tarkibiy birligi",
             "Azot asosi, uglevod va fosfat kislotadan iborat", "Tuzilma",
             ["Men uch qismdan iboratman"], None),
            ("Kodon", "i-RNK dagi uchta nukleotid ketma-ketligi",
             "Bitta aminokislotani belgilaydi", "Tuzilma",
             ["Men uchta nukleotiddan iboratman"], "64 xil kodon mavjud"),
            ("Antikodon", "t-RNK dagi uchta nukleotid",
             "i-RNK kodoniga to'ldiruvchi bo'lib birikadi", "Tuzilma", None, None),
            ("Gen", "Bitta oqsil sintezini boshqaruvchi DNK bo'lagi",
             "Belgining irsiylanishini ta'minlaydi", "Tuzilma",
             ["Men DNK ning bir bo'lagiman", "Men bitta belgini boshqaraman"], None),
            ("Transkripsiya", "DNK dan i-RNK ko'chirilishi",
             "Irsiy axborotni RNK tiliga o'tkazadi", "Jarayon",
             ["Men yadroda sodir bo'laman", "Mendan keyin i-RNK hosil bo'ladi"], None),
            ("Translyatsiya", "i-RNK bo'yicha oqsil yig'ilishi",
             "Nukleotid ketma-ketligini aminokislota ketma-ketligiga aylantiradi",
             "Jarayon", ["Men ribosomada sodir bo'laman"], None),
            ("Replikatsiya", "DNK ning ikki hissa ortishi",
             "Bo'linishdan oldin irsiy axborot nusxasini yaratadi", "Jarayon",
             ["Men interfazada sodir bo'laman"], None),
        ],
        "sequences": [
            {
                "title": "Oqsil sintezi bosqichlari",
                "description": "DNK dan tayyor oqsilgacha",
                "steps": [
                    "DNK zanjiri ochiladi",
                    "i-RNK sintez qilinadi (transkripsiya)",
                    "i-RNK yadrodan chiqib ribosomaga birikadi",
                    "t-RNK aminokislota olib keladi",
                    "Antikodon kodonga mos keladi",
                    "Aminokislotalar orasida peptid bog'i hosil bo'ladi",
                    "Tayyor oqsil ribosomadan ajraladi",
                ],
            },
        ],
    },
]


# ==========================================================================
#  4. BOTANIKA VA ZOOLOGIYA
# ==========================================================================

_BOTANIKA_ZOOLOGIYA = [
    {
        "title": "O'simlik organlari va to'qimalari",
        "terms": [
            ("Ildiz", "O'simlikni tuproqqa mahkamlovchi organ",
             "Suv va mineral tuzlarni so'radi", "Vegetativ organ",
             ["Men tuproq ostida joylashganman", "Men suvni so'raman"], None),
            ("Poya", "Ildiz bilan bargni bog'lovchi organ",
             "Moddalarni tashiydi va barglarni yorug'likka chiqaradi", "Vegetativ organ",
             None, None),
            ("Barg", "O'simlikning yassi yon organi",
             "Fotosintez, nafas olish va transpiratsiyani bajaradi", "Vegetativ organ",
             ["Menda og'izchalar bor", "Men fotosintez qilaman"], None),
            ("Gul", "O'simlikning ko'payish organi",
             "Changlanish va urug'lanishni ta'minlaydi", "Generativ organ",
             ["Men ko'payish uchun xizmat qilaman"], None),
            ("Meva", "Urug'ni o'rab turuvchi hosila",
             "Urug'ni himoya qiladi va tarqalishiga yordam beradi", "Generativ organ",
             None, None),
            ("Urug'", "Murtak saqlanadigan tuzilma",
             "Yangi o'simlik hosil qiladi", "Generativ organ",
             ["Ichimda murtak bor"], None),
            ("Meristema", "Bo'linish xususiyatiga ega to'qima",
             "O'simlikning o'sishini ta'minlaydi", "To'qima",
             ["Mening hujayralarim doim bo'linadi"], "Ildiz va poya uchida joylashadi"),
            ("Qoplovchi to'qima", "O'simlik yuzasini qoplovchi to'qima",
             "Ichki qismlarni himoya qiladi, gaz almashinuvini boshqaradi", "To'qima",
             None, "Og'izchalar shu to'qimada joylashgan"),
            ("O'tkazuvchi to'qima", "Naysimon hujayralardan iborat to'qima",
             "Suv va organik moddalarni tashiydi", "To'qima",
             ["Men naychalardan iboratman", "Men suv va oziq tashiyman"],
             "Ksilema suvni, floema organik moddani tashiydi"),
            ("Mexanik to'qima", "Qalin devorli hujayralardan iborat to'qima",
             "O'simlikka mustahkamlik beradi", "To'qima", None, None),
        ],
    },
    {
        "title": "Umurtqalilar sinflari",
        "terms": [
            ("Baliqlar", "Suvda yashovchi umurtqalilar sinfi",
             "Jabra bilan nafas oladi, suzgichlar bilan harakatlanadi", "Sovuq qonli",
             ["Men jabra bilan nafas olaman", "Menda suzgich pufagi bor"],
             "Ikki kamerali yurakka ega"),
            ("Suvda-quruqlikda yashovchilar", "Lichinkasi suvda rivojlanuvchi sinf",
             "Teri va o'pka orqali nafas oladi", "Sovuq qonli",
             ["Mening lichinkam suvda yashaydi", "Men teri orqali ham nafas olaman"],
             "Uch kamerali yurak"),
            ("Sudralib yuruvchilar", "Tanasi shox tangachalar bilan qoplangan sinf",
             "O'pka bilan nafas oladi, quruqlikda tuxum qo'yadi", "Sovuq qonli",
             ["Tanam tangachalar bilan qoplangan", "Men quruqlikda tuxum qo'yaman"],
             "Timsohdan tashqari hammasida uch kamerali yurak"),
            ("Qushlar", "Tanasi pat bilan qoplangan sinf",
             "Uchishga moslashgan, doimiy tana haroratini saqlaydi", "Issiq qonli",
             ["Tanam pat bilan qoplangan", "Menda havo qopchalari bor"],
             "Suyaklari ichi kovak — vazni yengil"),
            ("Sutemizuvchilar", "Bolasini sut bilan boquvchi sinf",
             "Doimiy tana haroratiga ega, diafragmasi bor", "Issiq qonli",
             ["Men bolamni sut bilan boqaman", "Menda diafragma bor"],
             "To'rt kamerali yurak"),
            ("Jabra", "Suvda nafas olish organi",
             "Suvda erigan kislorodni oladi", "Nafas organi", None, None),
            ("O'pka", "Quruqlikda nafas olish organi",
             "Havodan kislorod oladi", "Nafas organi", None, None),
            ("Diafragma", "Sutemizuvchilarga xos nafas mushagi",
             "Ko'krak bo'shlig'i hajmini o'zgartiradi", "Nafas organi", None,
             "Faqat sutemizuvchilarda uchraydi"),
        ],
        "sequences": [
            {
                "title": "Umurtqalilarning evolyutsion ketma-ketligi",
                "description": "Qaysi sinf qaysidan keyin paydo bo'lgan?",
                "steps": ["Baliqlar", "Suvda-quruqlikda yashovchilar",
                          "Sudralib yuruvchilar", "Qushlar", "Sutemizuvchilar"],
            },
        ],
    },
]


# --------------------------------------------------------------------------
#  Mavzu kaliti -> namuna levellar
# --------------------------------------------------------------------------

SEED_BY_TOPIC = {
    "hujayra": _HUJAYRA,
    "organ_tizimlari": _ORGAN_TIZIMLARI,
    "genetika": _GENETIKA,
    "botanika_zoologiya": _BOTANIKA_ZOOLOGIYA,
}


def seed_levels_for(topic_key: str):
    return SEED_BY_TOPIC.get((topic_key or "").strip().lower(), [])


def seed_summary(topic_key: str = "hujayra"):
    levels = seed_levels_for(topic_key)
    return {
        "topic_key": topic_key,
        "level_count": len(levels),
        "term_count": sum(len(l.get("terms", [])) for l in levels),
        "sequence_count": sum(len(l.get("sequences", [])) for l in levels),
        "titles": [l["title"] for l in levels],
        "available": bool(levels),
    }
