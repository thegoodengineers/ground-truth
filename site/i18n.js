/* Hindi for the site. English stays the source: each page block is found by its English text and swapped for its
   Hindi, phrases that app.js builds go through tr`...`, and the sentences the backend writes (check details,
   weather, fires) through detail(). Anything missing here simply stays in English.
   tests/test_i18n.py fails when a block below no longer exists in index.html, so edits there can't go stale silently. */
(() => {
  "use strict";
  let lang = "en";
  try { lang = localStorage.getItem("gt-lang") === "hi" ? "hi" : "en"; } catch (e) { /* stays English */ }

  // English text of a block (whitespace collapsed) -> its Hindi HTML
  const PAGE = {
    "Ground Truth: which Delhi air-quality numbers can you trust?": "Ground Truth: दिल्ली की हवा के कौन-से आँकड़ों पर भरोसा करें?",
    "Why": "क्यों",
    "How it works": "कैसे काम करता है",
    "Live map": "लाइव नक्शा",
    "Proof": "सबूत",
    "The air is already being measured.That's not the same as true.": '<span class="dim">हवा तो पहले से नापी जा रही है।</span>पर नापा हुआ हर आँकड़ा सही हो, ज़रूरी नहीं।',
    "Ground Truth checks every air-quality monitor in Delhi against the stations around it, its own past and physics, and tells you in plain words whether its number adds up.":
      "Ground Truth दिल्ली के हर वायु-गुणवत्ता मॉनिटर को आस-पास के स्टेशनों, उसके अपने पिछले रिकॉर्ड और भौतिकी से जाँचता है, और सीधे शब्दों में बताता है कि उसका आँकड़ा सही बैठता है या नहीं।",
    "Find your station": "अपना स्टेशन खोजें",
    "or watch the 60-second tour →": 'या 60 सेकंड का टूर देखें <span aria-hidden="true">→</span>',
    "Checked every hour, from the live data": "लाइव डेटा से, हर घंटे जाँच",
    "stations checked": "स्टेशन जाँचे गए",
    "don't add up": "के आँकड़े मेल नहीं खाते",
    "worth a look": "एक बार देखने लायक",
    "planted anomalies caught in tests": "टेस्ट में डाली गई गड़बड़ियाँ पकड़ी गईं",
    "The problem, and our answer": "समस्या, और हमारा हल",
    "Delhi decides on these numbers.Nobody checks the monitors.": '<span class="dim">दिल्ली इन्हीं आँकड़ों पर फ़ैसले लेती है।</span>मॉनिटरों को कोई नहीं जाँचता।',
    "The problem": "समस्या",
    "A number on a screen doesn't tell you if the monitor behind it works.": "स्क्रीन पर दिखता आँकड़ा यह नहीं बताता कि उसके पीछे का मॉनिटर ठीक काम कर रहा है या नहीं।",
    "Real decisions ride on it. A principal keeps assembly outdoors, a parent takes a child to the park, the city stops construction, all on what about 40 monitors report.":
      "<b>असली फ़ैसले इसी पर टिके हैं।</b> प्रिंसिपल असेंबली बाहर रखते हैं, माता-पिता बच्चे को पार्क ले जाते हैं, शहर निर्माण रोकता है, सब कुछ लगभग 40 मॉनिटरों की रीडिंग पर।",
    "Monitors go wrong. Sensors drift, break, get dusty or get moved, and the number keeps publishing as if nothing happened.":
      "<b>मॉनिटर ख़राब होते हैं।</b> सेंसर खिसकते हैं, टूटते हैं, धूल से भरते हैं या जगह बदलते हैं, और आँकड़ा ऐसे छपता रहता है जैसे कुछ हुआ ही नहीं।",
    "Sometimes worse. In October 2025, water tankers were filmed spraying near a Delhi monitor, which makes the air read cleaner than it is.":
      "<b>कभी-कभी इससे भी बुरा।</b> अक्टूबर 2025 में दिल्ली के एक मॉनिटर के पास पानी के टैंकर छिड़काव करते हुए फ़िल्माए गए, जिससे हवा असल से साफ़ पढ़ी जाती है।",
    "Today, nobody can tell a working monitor from a broken one.": "आज कोई नहीं बता सकता कि कौन-सा मॉनिटर ठीक है और कौन-सा ख़राब।",
    "Our answer: Ground Truth": "हमारा हल: Ground Truth",
    "Every monitor, checked every hour, with a plain answer.": "हर मॉनिटर, हर घंटे जाँचा गया, एक सीधे जवाब के साथ।",
    "1Physics: is the reading even possible? Fine dust can never be more than all dust.":
      '<span class="why-n">1</span><div><b>भौतिकी:</b> क्या यह रीडिंग संभव भी है? बारीक धूल कभी कुल धूल से ज़्यादा नहीं हो सकती।</div>',
    "2Neighbours: does it agree with the four monitors around it?": '<span class="why-n">2</span><div><b>पड़ोसी:</b> क्या यह आस-पास के चार मॉनिटरों से मेल खाता है?</div>',
    "3History: did it suddenly change against its own last three weeks?": '<span class="why-n">3</span><div><b>इतिहास:</b> क्या यह अपने पिछले तीन हफ़्तों के मुकाबले अचानक बदल गया?</div>',
    "When a monitor is in doubt, we show what the four around it read right now, so you still have a number you can act on.":
      "जब किसी मॉनिटर पर शक हो, तो हम दिखाते हैं कि उसके आस-पास के चार मॉनिटर अभी क्या पढ़ रहे हैं, ताकि आपके पास भरोसे लायक आँकड़ा फिर भी रहे।",
    "An example morning in East Delhi": "पूर्वी दिल्ली की एक सुबह, उदाहरण के तौर पर",
    "7:30The principal checks the nearest monitor. It says the air is Moderate.": '<span class="t">7:30</span><p>प्रिंसिपल सबसे नज़दीकी मॉनिटर देखते हैं। वह हवा को <b>मध्यम</b> बताता है।</p>',
    "7:31Ground Truth marks that monitor : it disagrees with the four around it.": '<span class="t">7:31</span><p>Ground Truth उस मॉनिटर को <span data-pill="flag"></span> बताता है: वह आस-पास के चारों से मेल नहीं खाता।</p>',
    "7:31The four monitors around the school read Very poor.": '<span class="t">7:31</span><p>स्कूल के आस-पास के चार मॉनिटर <b>बहुत ख़राब</b> दिखाते हैं।</p>',
    "7:32Assembly moves indoors. The decision is made on a number that adds up.": '<span class="t">7:32</span><p>असेंबली अंदर होती है। फ़ैसला उस आँकड़े पर होता है जो सही बैठता है।</p>',
    "Why we built it · October 2025": "हमने इसे क्यों बनाया · अक्टूबर 2025",
    "Spray water around a monitor,and its number drops. The air doesn't.": '<span class="dim">मॉनिटर के पास पानी छिड़कें,</span>तो उसका आँकड़ा गिरता है। हवा नहीं सुधरती।',
    "In October 2025, water tankers were filmed spraying near a Delhi monitor. Wet the air at the inlet and the dust settles right there, so the monitor reads cleaner than the air the city is breathing.":
      "अक्टूबर 2025 में दिल्ली के एक मॉनिटर के पास पानी के टैंकर छिड़काव करते फ़िल्माए गए। इनलेट पर हवा गीली करें तो धूल वहीं बैठ जाती है, और मॉनिटर उस हवा से साफ़ पढ़ता है जिसमें शहर साँस ले रहा है।",
    "Pause": "रोकें",
    "An illustration, not footage, and the numbers are examples. We did test whether the monitors named in the October 2025 reports show this pattern. On a method fixed before looking, they didn't stand out (Anand Vihar ranked 6th and Jahangirpuri 13th of 38). So a flag on this site means a monitor's numbers don't add up, never that someone sprayed it.":
      "यह एक चित्रण है, असली फ़ुटेज नहीं, और आँकड़े उदाहरण हैं। हमने जाँचा कि अक्टूबर 2025 की ख़बरों में बताए गए मॉनिटर यह पैटर्न दिखाते हैं या नहीं। पहले से तय तरीके पर वे अलग नहीं दिखे (38 में आनंद विहार 6वें और जहाँगीरपुरी 13वें स्थान पर)। इसलिए इस साइट पर फ़्लैग का मतलब है कि मॉनिटर के आँकड़े मेल नहीं खाते, कभी यह नहीं कि किसी ने उस पर छिड़काव किया।",
    "How it works, in ten seconds": "दस सेकंड में समझें कि यह कैसे काम करता है",
    "A reading on its own can't tell you if it's right.The monitors around it can.": '<span class="dim">अकेली रीडिंग नहीं बता सकती कि वह सही है या नहीं।</span>आस-पास के मॉनिटर बता सकते हैं।',
    "A monitor reports a number": "एक मॉनिटर आँकड़ा भेजता है",
    "Every hour, each of Delhi's monitors publishes its PM2.5 reading.": "हर घंटे दिल्ली का हर मॉनिटर अपनी PM2.5 रीडिंग जारी करता है।",
    "We ask its four neighbours": "हम उसके चार पड़ोसियों से पूछते हैं",
    "We compare it with the four nearest monitors, within 12 km.": "हम उसकी तुलना 12 km के अंदर के चार सबसे नज़दीकी मॉनिटरों से करते हैं।",
    "You get a plain answer": "आपको सीधा जवाब मिलता है",
    "If the numbers don't add up, we say so, and show you which number to use instead.": "अगर आँकड़े मेल नहीं खाते, तो हम साफ़ बताते हैं, और दिखाते हैं कि उसकी जगह कौन-सा आँकड़ा इस्तेमाल करें।",
    "Reading the answers": "जवाबों को कैसे पढ़ें",
    "Three answers, and an honest \"can't tell\".Here's what to do with each.": '<span class="dim">तीन जवाब, और एक ईमानदार "पता नहीं"।</span>हर एक पर क्या करें, यह रहा।',
    "Find the monitor you rely on.See its answer, and why.": '<span class="dim">वह मॉनिटर खोजें जिस पर आप भरोसा करते हैं।</span>उसका जवाब देखें, और उसकी वजह।',
    "Each mast is a monitor, and its column is as tall as its PM2.5 reading. The smog is thicker where the air is worse. Click a monitor for its answer, or click the city to explore it in 3D.":
      "हर खंभा एक मॉनिटर है, और उसका स्तंभ उसकी PM2.5 रीडिंग जितना ऊँचा है। जहाँ हवा ज़्यादा ख़राब है वहाँ धुंध घनी है। जवाब के लिए किसी मॉनिटर पर क्लिक करें, या शहर पर क्लिक करके उसे 3D में देखें।",
    "Exit 3D ✕": '3D से बाहर <span aria-hidden="true">✕</span>',
    "Monitor ↕": 'मॉनिटर <span aria-hidden="true">↕</span>',
    "Area ↕": 'इलाक़ा <span aria-hidden="true">↕</span>',
    "Answer ↕": 'जवाब <span aria-hidden="true">↕</span>',
    "PM2.5 (µg/m³) ↕": 'PM2.5 <small>(µg/m³)</small> <span aria-hidden="true">↕</span>',
    "Neighbours PM2.5 ↕": 'पड़ोसियों का PM2.5 <span aria-hidden="true">↕</span>',
    "Explore Delhi in 3D ⤢": 'दिल्ली को 3D में देखें <span aria-hidden="true">⤢</span>',
    "List view": "सूची",
    "Every monitor, by area": "हर मॉनिटर, इलाक़े के हिसाब से",
    "Filter monitors": "मॉनिटर छाँटें",
    "The three checks": "तीन जाँचें",
    "Three questions, asked every hour.Each one, with a real example.": '<span class="dim">तीन सवाल, हर घंटे पूछे जाते हैं।</span>हर एक, असली उदाहरण के साथ।',
    "Physics": "भौतिकी",
    "Can this reading even be real?": "क्या यह रीडिंग असली हो भी सकती है?",
    "Fine dust (PM2.5) is part of all dust (PM10), so it can never be bigger. A monitor that says otherwise, or repeats the same number for hours, is broken.":
      "बारीक धूल (PM2.5) कुल धूल (PM10) का हिस्सा है, इसलिए वह कभी उससे बड़ी नहीं हो सकती। जो मॉनिटर इसका उल्टा बताए, या घंटों एक ही आँकड़ा दोहराए, वह ख़राब है।",
    "Formula and thresholds": "सूत्र और सीमाएँ",
    "Each hour fails if any of these is true:": "कोई घंटा <b>फ़ेल</b> होता है अगर इनमें से कोई भी सच हो:",
    "PM2.5 > 1.05 × PM10 (5% allowed for instrument noise)": "PM2.5 &gt; 1.05 × PM10 (उपकरण की गड़बड़ के लिए 5% की छूट)",
    "PM10 outside 1–2000 µg/m³, or PM2.5 outside 1–1500 µg/m³": "PM10, 1–2000 µg/m³ से बाहर, या PM2.5, 1–1500 µg/m³ से बाहर",
    "Stuck: the same PM2.5, PM10, NO2 or CO value for 3 or more hours in a row": "अटका हुआ: लगातार 3 या ज़्यादा घंटे PM2.5, PM10, NO2 या CO का एक ही मान",
    "Over the last 7 days (at least 24 hours with PM data): worth a look if more than 1% of hours fail, doesn't add up if more than 5% fail.":
      "पिछले 7 दिनों में (कम से कम 24 घंटे का PM डेटा हो): 1% से ज़्यादा घंटे फ़ेल हों तो <b>एक बार देखें</b>, 5% से ज़्यादा फ़ेल हों तो <b>आँकड़े मेल नहीं खाते</b>।",
    "Uses PM2.5 and PM10.": "PM2.5 और PM10 का इस्तेमाल।",
    "Neighbours": "पड़ोसी",
    "Does it agree with the monitors around it?": "क्या यह आस-पास के मॉनिटरों से मेल खाता है?",
    "Hour by hour, against the four nearest. Daytime air mixes, so some difference is normal; we only flag a monitor that drifts far more than the rest of the city.":
      "घंटे-दर-घंटे, चार सबसे नज़दीकी मॉनिटरों के मुकाबले। दिन में हवा मिलती-घुलती है, इसलिए थोड़ा फ़र्क़ सामान्य है; हम सिर्फ़ उसी मॉनिटर को फ़्लैग करते हैं जो बाक़ी शहर से कहीं ज़्यादा भटके।",
    "Neighbours: the 4 nearest monitors with data within 12 km (great-circle distance). Monitors closer than 0.5 km are skipped, because they are twins on the same site.":
      "<b>पड़ोसी:</b> 12 km (great-circle दूरी) के अंदर डेटा वाले 4 सबसे नज़दीकी मॉनिटर। 0.5 km से पास वाले छोड़ दिए जाते हैं, क्योंकि वे एक ही जगह पर जुड़वाँ हैं।",
    "Hourly gap: g = ln(PM10 ÷ median PM10 of the neighbours), when at least 2 neighbours report that hour.":
      "<b>हर घंटे का अंतर:</b> g = ln(PM10 ÷ पड़ोसियों का median PM10), जब उस घंटे कम से कम 2 पड़ोसी रीडिंग भेजें।",
    "Daily contrast: d = median g over 11:00–16:59, minus median g over 22:00–05:59 (at least 4 hours each). Its weekly value is the median d over the last 7 days.":
      "<b>रोज़ का फ़र्क़:</b> d = 11:00–16:59 का median g, घटा 22:00–05:59 का median g (हर एक में कम से कम 4 घंटे)। हफ़्ते का मान पिछले 7 दिनों का median d है।",
    "Mixing correction: by day, air mixes higher, so a monitor that reads high at night drifts towards its neighbours. We fit one Theil–Sen line of d against the night gap across the city, and score each monitor's distance from that line.":
      "<b>मिश्रण सुधार:</b> दिन में हवा ऊपर तक मिलती है, इसलिए रात में ज़्यादा पढ़ने वाला मॉनिटर दिन में पड़ोसियों के क़रीब आ जाता है। हम पूरे शहर में रात के अंतर के मुकाबले d की एक Theil–Sen रेखा बनाते हैं, और हर मॉनिटर की उस रेखा से दूरी आँकते हैं।",
    "Score: robust z = (residual − median) ÷ (1.4826 × MAD) across all monitors. Worth a look at |z| ≥ 2, doesn't add up at |z| ≥ 3.":
      "<b>स्कोर:</b> सभी मॉनिटरों में robust z = (residual − median) ÷ (1.4826 × MAD)। |z| ≥ 2 पर <b>एक बार देखें</b>, |z| ≥ 3 पर <b>आँकड़े मेल नहीं खाते</b>।",
    "Two passes: monitors flagged in the first pass are taken out of everyone's reference and out of the city line in the second.":
      "<b>दो बार:</b> पहली बार में फ़्लैग हुए मॉनिटर दूसरी बार में सबके संदर्भ और शहर की रेखा से हटा दिए जाते हैं।",
    "Uses PM10. Medians and MAD, not means and standard deviations, so one bad hour or one bad monitor can't move the reference.":
      "PM10 का इस्तेमाल। औसत और standard deviation नहीं, median और MAD, ताकि एक ख़राब घंटा या एक ख़राब मॉनिटर संदर्भ न हिला सके।",
    "History": "इतिहास",
    "Has it suddenly changed?": "क्या यह अचानक बदल गया है?",
    "We compare the last 7 days with the 3 weeks before. A sudden jump against its own past means something changed at that monitor.":
      "हम पिछले 7 दिनों की तुलना उससे पहले के 3 हफ़्तों से करते हैं। अपने ही पिछले रिकॉर्ड के मुकाबले अचानक उछाल का मतलब है कि उस मॉनिटर पर कुछ बदला है।",
    "The same daily contrast d as Neighbours, for PM10 (log ratio) and for humidity (percentage points).": "पड़ोसी वाली जाँच का वही रोज़ का फ़र्क़ d, PM10 (log ratio) और नमी (प्रतिशत अंक) के लिए।",
    "Shift: median d over the last 7 days, minus median d over the 21 days before. This needs at least 4 recent days and 10 earlier days.":
      "<b>बदलाव:</b> पिछले 7 दिनों का median d, घटा उससे पहले के 21 दिनों का median d। इसके लिए कम से कम 4 हाल के और 10 पहले के दिन चाहिए।",
    "Score: z = shift ÷ robust SD of the earlier 21 days, where robust SD = 1.4826 × MAD. Its floor is 0.02 for PM10 and 1 point for humidity, so a very steady monitor isn't flagged for a tiny change. The larger |z| of the two measures counts.":
      "<b>स्कोर:</b> z = बदलाव ÷ पहले के 21 दिनों का robust SD, जहाँ robust SD = 1.4826 × MAD। इसकी न्यूनतम सीमा PM10 के लिए 0.02 और नमी के लिए 1 अंक है, ताकि बहुत स्थिर मॉनिटर छोटे-से बदलाव पर फ़्लैग न हो। दोनों में से बड़ा |z| गिना जाता है।",
    "Worth a look at |z| ≥ 2, doesn't add up at |z| ≥ 3.": "|z| ≥ 2 पर <b>एक बार देखें</b>, |z| ≥ 3 पर <b>आँकड़े मेल नहीं खाते</b>।",
    "Uses PM10 and humidity. A sudden humidity shift against the neighbours usually means something changed at the monitor itself, such as its inlet, its dryer or where it stands.":
      "PM10 और नमी का इस्तेमाल। पड़ोसियों के मुकाबले नमी में अचानक बदलाव का आम तौर पर मतलब है कि मॉनिटर में ही कुछ बदला है, जैसे उसका इनलेट, उसका ड्रायर या उसकी जगह।",
    "How the three checks become one answer": "तीन जाँचें एक जवाब कैसे बनती हैं",
    "A monitor's answer is the most serious of its three checks. So a single check can flag a monitor, even one about humidity, and the monitor's card always names the check and the measure that raised it. Physics uses PM2.5 and PM10; Neighbours uses PM10; History uses PM10 and humidity.":
      "मॉनिटर का जवाब उसकी तीनों जाँचों में <b>सबसे गंभीर</b> वाला होता है। इसलिए एक अकेली जाँच भी मॉनिटर को फ़्लैग कर सकती है, नमी वाली भी, और मॉनिटर का कार्ड हमेशा बताता है कि किस जाँच और किस माप ने उसे उठाया। भौतिकी PM2.5 और PM10 देखती है; पड़ोसी PM10; इतिहास PM10 और नमी।",
    "The number you act on is PM2.5, the fine dust that health advice is based on. The checks lean on PM10 because the coarse dust it measures is what dust control and water spraying change the most.":
      "जिस आँकड़े पर आप फ़ैसला लेते हैं वह PM2.5 है, वह बारीक धूल जिस पर सेहत की सलाह टिकी है। जाँचें PM10 पर ज़्यादा टिकी हैं क्योंकि उसकी मोटी धूल को ही धूल-नियंत्रण और पानी का छिड़काव सबसे ज़्यादा बदलते हैं।",
    "When fewer than 2 neighbours, or too few days of data, are available, a check answers not enough data instead of guessing. A monitor gets that answer only if none of its checks can run.":
      "जब 2 से कम पड़ोसी हों, या डेटा के बहुत कम दिन हों, तो जाँच अंदाज़ा लगाने की जगह <b>पर्याप्त डेटा नहीं</b> कहती है। मॉनिटर को यह जवाब तभी मिलता है जब उसकी कोई भी जाँच न चल सके।",
    "Who it's for": "यह किसके लिए है",
    "For anyone who acts on the number.Before they act on it.": '<span class="dim">हर उस व्यक्ति के लिए जो इस आँकड़े पर फ़ैसला लेता है।</span>फ़ैसला लेने से पहले।',
    "A school principal": "स्कूल के प्रिंसिपल",
    "Deciding at 7:30 whether assembly and PE stay outdoors. If the nearest monitor doesn't add up, they use what the monitors around the school read.":
      "7:30 बजे तय करते हैं कि असेंबली और खेल बाहर होंगे या नहीं। अगर नज़दीकी मॉनिटर के आँकड़े मेल नहीं खाते, तो वे स्कूल के आस-पास के मॉनिटरों की रीडिंग लेते हैं।",
    "A parent": "माता-पिता",
    "Planning a walk or a park visit with a child, or deciding when to run the air purifier. One glance tells them whether today's number can be trusted.":
      "बच्चे के साथ सैर या पार्क की योजना, या एयर प्यूरीफ़ायर कब चलाना है। एक नज़र में पता चलता है कि आज के आँकड़े पर भरोसा किया जा सकता है या नहीं।",
    "A reporter or official": "पत्रकार या अधिकारी",
    "Checking whether a monitor's readings changed, and when, before writing about it. Every answer links to the hour-by-hour evidence.":
      "लिखने से पहले जाँचते हैं कि किसी मॉनिटर की रीडिंग बदली या नहीं, और कब। हर जवाब घंटे-दर-घंटे के सबूत से जुड़ा है।",
    "Does it actually work?": "क्या यह सच में काम करता है?",
    "We tried to fool it 30 times.It caught all 30.": '<span class="dim">हमने इसे 30 बार धोखा देने की कोशिश की।</span>इसने सभी 30 पकड़ लिए।',
    "We took real data from November 2025 and, one quiet monitor at a time, secretly lowered its daytime dust by 40%. Ground Truth flagged every one of them, and wrongly flagged another monitor only 3 times across all 30 runs.":
      "हमने नवंबर 2025 का असली डेटा लिया और एक-एक करके हर ठीक मॉनिटर की दिन की धूल चुपचाप 40% घटा दी। Ground Truth ने हर एक को फ़्लैग किया, और सभी 30 बार में किसी दूसरे मॉनिटर को सिर्फ़ 3 बार ग़लती से फ़्लैग किया।",
    "We also scored every day of October and November 2025 as this site would have. Most flags were readings that can't be real, and smaller planted drops were caught less often (30%: 29 of 30, 20%: 10 of 30). Read the validation report":
      'हमने अक्टूबर और नवंबर 2025 के हर दिन को वैसे ही जाँचा जैसे यह साइट जाँचती। ज़्यादातर फ़्लैग ऐसी रीडिंग थे जो असली हो ही नहीं सकतीं, और छोटी गिरावटें कम बार पकड़ी गईं (30%: 30 में से 29, 20%: 30 में से 10)। <a href="https://github.com/thegoodengineers/ground-truth/blob/main/docs/VALIDATION.md">जाँच की रिपोर्ट पढ़ें</a>',
    "This test, and 84 others, run automatically every time the code changes. See the tests":
      'यह टेस्ट, और 84 दूसरे, कोड बदलने पर हर बार अपने-आप चलते हैं। <a href="https://github.com/thegoodengineers/ground-truth/tree/main/tests">टेस्ट देखें</a>',
    "Built on AWS": "AWS पर बना",
    "Nobody presses a button.It checks itself every hour.": '<span class="dim">कोई बटन नहीं दबाता।</span>यह हर घंटे ख़ुद जाँच करता है।',
    "The whole system is one AWS SAM template, deployed in us-east-1 next to the public OpenAQ archive it reads from.":
      "पूरा सिस्टम एक AWS SAM template है, us-east-1 में उस सार्वजनिक OpenAQ archive के पास लगा है जिससे यह पढ़ता है।",
    "Every hourAmazon EventBridgestarts the check": '<span class="pipe-k">हर घंटे</span><b>Amazon EventBridge</b><span>जाँच शुरू करता है</span>',
    "Fetch + checkAWS Lambdareads new readings from OpenAQ, with the key from Parameter Store, and runs the three checks":
      '<span class="pipe-k">लाना + जाँचना</span><b>AWS Lambda</b><span>Parameter Store की key से OpenAQ की नई रीडिंग पढ़ता है, और तीनों जाँचें चलाता है</span>',
    "StoreAmazon S3keeps 29 days of history and the results": '<span class="pipe-k">रखना</span><b>Amazon S3</b><span>29 दिन का इतिहास और नतीजे रखता है</span>',
    "ServeAmazon CloudFrontdelivers this page and the data": '<span class="pipe-k">पहुँचाना</span><b>Amazon CloudFront</b><span>यह पेज और डेटा पहुँचाता है</span>',
    "ReadYousee every monitor's answer": '<span class="pipe-k">पढ़ना</span><b>आप</b><span>हर मॉनिटर का जवाब देखते हैं</span>',
    "Questions": "सवाल",
    "Still wondering?Plain answers.": '<span class="dim">अब भी कोई सवाल?</span>सीधे जवाब।',
    "Does a red answer mean someone tampered with the monitor?": "क्या लाल जवाब का मतलब है कि किसी ने मॉनिटर से छेड़छाड़ की?",
    "No. It means the monitor's numbers don't add up against physics, its neighbours or its own past. Sensors drift, break and get moved. We tested whether the monitors named in the news in October 2025 show a spraying pattern, and with our method they don't stand out.":
      "नहीं। इसका मतलब है कि मॉनिटर के आँकड़े भौतिकी, पड़ोसियों या अपने पिछले रिकॉर्ड से मेल नहीं खाते। सेंसर खिसकते हैं, टूटते हैं और जगह बदलते हैं। हमने जाँचा कि अक्टूबर 2025 की ख़बरों वाले मॉनिटर छिड़काव जैसा पैटर्न दिखाते हैं या नहीं, और हमारे तरीके से वे अलग नहीं दिखते।",
    "Which number should I use if my monitor is flagged?": "अगर मेरा मॉनिटर फ़्लैग हो, तो कौन-सा आँकड़ा इस्तेमाल करूँ?",
    "Use what the four nearest monitors read right now. The panel shows it next to your monitor's own reading. It is the middle value of real monitors, not an official reading.":
      "चार सबसे नज़दीकी मॉनिटर अभी जो पढ़ रहे हैं, वह इस्तेमाल करें। पैनल इसे आपके मॉनिटर की रीडिंग के बगल में दिखाता है। यह असली मॉनिटरों का बीच वाला मान है, कोई सरकारी रीडिंग नहीं।",
    "How fresh is the data?": "डेटा कितना ताज़ा है?",
    "The check runs every hour on new readings from the CPCB and DPCC monitors, via OpenAQ. The time of the latest reading is at the top of the page.":
      "जाँच हर घंटे OpenAQ के ज़रिए CPCB और DPCC मॉनिटरों की नई रीडिंग पर चलती है। सबसे नई रीडिंग का समय पेज में सबसे ऊपर है।",
    "Why does a polluted area look cleaner in the afternoon?": "प्रदूषित इलाक़ा दोपहर में साफ़ क्यों दिखता है?",
    "By day the air mixes higher, so pollution near busy roads spreads out and a hotspot reads closer to its neighbours. We correct for this so it isn't mistaken for a problem.":
      "दिन में हवा ऊपर तक मिलती है, इसलिए व्यस्त सड़कों के पास का प्रदूषण फैल जाता है और हॉटस्पॉट अपने पड़ोसियों के क़रीब पढ़ता है। हम इसका सुधार करते हैं ताकि इसे गड़बड़ी न समझा जाए।",
    "Is the code open?": "क्या कोड खुला है?",
    "Yes. Everything, including the data analysis behind these checks, is on GitHub.": "हाँ। सब कुछ, इन जाँचों के पीछे का डेटा विश्लेषण भी, GitHub पर है।",
    "Open data": "खुला डेटा",
    "The numbers are public.Download today's answers.": '<span class="dim">आँकड़े सार्वजनिक हैं।</span>आज के जवाब डाउनलोड करें।',
    "Every monitor's status and latest readings, updated every hour. Use them freely; cite the source.": "हर मॉनिटर का हाल और ताज़ा रीडिंग, हर घंटे अपडेट। खुलकर इस्तेमाल करें; स्रोत का ज़िक्र करें।",
    "Download CSV": "CSV डाउनलोड करें",
    "View JSON": "JSON देखें",
    "CSV columns": "CSV के कॉलम",
    "Column": "कॉलम",
    "Description": "विवरण",
    "OpenAQ location ID": "OpenAQ location ID",
    "Station name": "स्टेशन का नाम",
    "Agency (CPCB, DPCC, HSPCB, UPPCB, IMD, IITM)": "एजेंसी (CPCB, DPCC, HSPCB, UPPCB, IMD, IITM)",
    "Coordinates (WGS84)": "निर्देशांक (WGS84)",
    "Overall verdict: ok, watch, flag or nodata": "कुल नतीजा: <code>ok</code>, <code>watch</code>, <code>flag</code> या <code>nodata</code>",
    "Physics check result": "भौतिकी जाँच का नतीजा",
    "Neighbour-comparison check result": "पड़ोसी-तुलना जाँच का नतीजा",
    "History check result": "इतिहास जाँच का नतीजा",
    "Latest hourly reading in µg/m³ (may be blank)": "µg/m³ में ताज़ा घंटे की रीडिंग (ख़ाली हो सकती है)",
    "Latest NO₂ (µg/m³) and CO (mg/m³)": "ताज़ा NO₂ (µg/m³) और CO (mg/m³)",
    "Latest relative humidity (%)": "ताज़ा सापेक्ष नमी (%)",
    "Median of the four nearest monitors' latest readings": "चार सबसे नज़दीकी मॉनिटरों की ताज़ा रीडिंग का median",
    "IST hour of the monitor's newest PM reading; with none in the last 3 hours, status is nodata":
      "मॉनिटर की सबसे नई PM रीडिंग का IST घंटा; पिछले 3 घंटों में कोई न हो, तो <code>status</code> <code>nodata</code> है",
    "CPCB AQI band of the 24-hour average, for this monitor and for its four neighbours": "24 घंटे के औसत का CPCB AQI स्तर, इस मॉनिटर और इसके चार पड़ोसियों के लिए",
    "IST timestamp of the latest scored hour": "आख़िरी जाँचे गए घंटे का IST समय",
    "Our results (status, checks, this CSV) are released under CC BY 4.0. Underlying PM readings are from OpenAQ and subject to their terms. Suggested citation: Ground Truth, thegoodengineers, , https://github.com/thegoodengineers/ground-truth.":
      'हमारे नतीजे (हाल, जाँचें, यह CSV) <a href="https://creativecommons.org/licenses/by/4.0/" rel="noopener">CC BY 4.0</a> के तहत जारी हैं। मूल PM रीडिंग OpenAQ की हैं और उनकी शर्तों के अधीन हैं। हवाला ऐसे दें: <em>Ground Truth, thegoodengineers, <span id="cite-date"></span>, https://github.com/thegoodengineers/ground-truth</em>।',
    "Before you act on a number,check that it adds up.": '<span class="dim">किसी आँकड़े पर फ़ैसला लेने से पहले,</span>देख लें कि वह सही बैठता है।',
    "Find the station you rely on. It takes ten seconds.": "जिस स्टेशन पर आप भरोसा करते हैं, उसे खोजें। दस सेकंड लगते हैं।",
    "Find your station ↑": 'अपना स्टेशन खोजें <span class="arr">↑</span>',
    "Which of Delhi's air-quality numbers can you trust? Environmental Hacks 2026, Air track.": "दिल्ली की हवा के कौन-से आँकड़ों पर भरोसा करें? Environmental Hacks 2026, Air track।",
    "Data": "डेटा",
    "CPCB / DPCC monitors via OpenAQ": 'CPCB / DPCC मॉनिटर, <a href="https://openaq.org">OpenAQ</a> के ज़रिए',
    "Wind and mixing height: Open-Meteo (CC BY 4.0)": 'हवा और मिश्रण की ऊँचाई: <a href="https://open-meteo.com">Open-Meteo</a> (CC BY 4.0)',
    "Farm fires: NASA FIRMS, VIIRS (Suomi NPP)": 'खेतों की आग: <a href="https://firms.modaps.eosdis.nasa.gov/">NASA FIRMS</a>, VIIRS (Suomi NPP)',
    "Voice of the tour: ElevenLabs": 'टूर की आवाज़: <a href="https://elevenlabs.io">ElevenLabs</a>',
    "3D scene drawn with three.js": '3D दृश्य <a href="https://threejs.org">three.js</a> से बना',
    "Wards: DataMeet (CC BY-SA 2.5 IN)": 'वार्ड: <a href="https://github.com/datameet/Municipal_Spatial_Data">DataMeet</a> (CC BY-SA 2.5 IN)',
    "Project": "प्रोजेक्ट",
    "Method": "तरीका",
    "The method": "तरीका",
    "Three checks, every hour.Every formula, in the open.": '<span class="dim">तीन जाँचें, हर घंटे।</span>हर सूत्र, सबके सामने।',
    "Physics, neighbours and history: what each check asks, its exact formula and thresholds, how they combine into one answer, and how they did on two months of real data.":
      "भौतिकी, पड़ोसी और इतिहास: हर जाँच क्या पूछती है, उसका सटीक सूत्र और सीमाएँ, वे मिलकर एक जवाब कैसे बनती हैं, और दो महीने के असली डेटा पर उनका प्रदर्शन कैसा रहा।",
    "Read the method →": 'तरीका पढ़ें <span class="arr">→</span>',
    "Method · Ground Truth": "तरीका · Ground Truth",
    "How every monitor is checked,in full.": '<span class="dim">हर मॉनिटर की जाँच कैसे होती है,</span>पूरी तरह।',
    "Each hour, every monitor in Delhi and the NCR goes through three checks. Here is what each one asks, its exact formula and thresholds, how they combine into one answer, how they did on two months of real data, and where to get the numbers yourself.":
      "हर घंटे दिल्ली और NCR का हर मॉनिटर तीन जाँचों से गुज़रता है। यहाँ है कि हर जाँच क्या पूछती है, उसका सटीक सूत्र और सीमाएँ, वे मिलकर एक जवाब कैसे बनती हैं, दो महीने के असली डेटा पर उनका प्रदर्शन, और आँकड़े ख़ुद कहाँ से लें।",
    "← Back to the live map": "← लाइव नक्शे पर वापस",
    "Tested on real data": "असली डेटा पर परखा गया",
    "Two months, every day, scored as this site would.Here is how often it raises a monitor.": '<span class="dim">दो महीने, हर दिन, वैसे ही जाँचा जैसे यह साइट जाँचती।</span>यह रहा कि यह कितनी बार किसी मॉनिटर को उठाती है।',
    "Every day from 1 October to 30 November 2025 was scored at 17:00 IST from the public OpenAQ archive, with the same thresholds as the live site.":
      "1 अक्टूबर से 30 नवंबर 2025 तक हर दिन को सार्वजनिक OpenAQ archive से 17:00 IST पर, लाइव साइट जैसी ही सीमाओं के साथ जाँचा गया।",
    "On an ordinary day": "एक आम दिन",
    "Doesn't add up": "आँकड़े मेल नहीं खाते",
    "Worth a look": "एक बार देखें",
    "Agrees with neighbours": "पड़ोसियों से मेल खाता है",
    "20.8% of monitors": "20.8% मॉनिटर",
    "Flags from the physics check": "भौतिकी जाँच से फ़्लैग",
    "Flags from neighbours and history": "पड़ोसी और इतिहास जाँच से फ़्लैग",
    "7.6 a day": "रोज़ 7.6",
    "2.9 a day": "रोज़ 2.9",
    "Most flags are readings that can't be real, such as PM2.5 above PM10 or a sensor stuck on one value: a fault whatever the air is doing.":
      "ज़्यादातर फ़्लैग ऐसी रीडिंग हैं जो असली हो ही नहीं सकतीं, जैसे PM2.5 का PM10 से ज़्यादा होना या एक ही मान पर अटका सेंसर: हवा जैसी भी हो, यह ख़राबी है।",
    "Catching a planted drop": "डाली गई गिरावट को पकड़ना",
    "Daytime PM10 cut": "दिन के PM10 में कटौती",
    "Flagged": "फ़्लैग हुए",
    "10 of 30": "30 में से 10",
    "29 of 30": "30 में से 29",
    "30 of 30": "30 में से 30",
    "Each quiet monitor in turn had its daytime PM10 lowered for a week, and the whole city was scored again.":
      "हर ठीक मॉनिटर का, एक-एक करके, दिन का PM10 एक हफ़्ते के लिए घटाया गया, और पूरे शहर को फिर से जाँचा गया।",
    "Every number here comes from src/validate.py; the full report is docs/VALIDATION.md.":
      'यहाँ का हर आँकड़ा <code>src/validate.py</code> से आता है; पूरी रिपोर्ट <a href="https://github.com/thegoodengineers/ground-truth/blob/main/docs/VALIDATION.md">docs/VALIDATION.md</a> है।',
    "60-second tour": "60 सेकंड का टूर",
    "This monitor": "यह मॉनिटर",
    "Monitors nearby": "आस-पास के मॉनिटर",
  };

  // phrases app.js builds: the English template with {0}, {1}... for the values -> the Hindi template
  const UI = {
    "Readings through {0} IST": "{0} IST तक की रीडिंग",
    "Readings through {0}": "{0} तक की रीडिंग",
    "Data unavailable": "डेटा उपलब्ध नहीं",
    "Offline": "ऑफ़लाइन",
    "Delhi + NCR · {0} monitors · checked hourly": "दिल्ली + NCR · {0} मॉनिटर · हर घंटे जाँच",
    "just now": "अभी-अभी",
    "{0} min ago": "{0} मिनट पहले",
    "{0} h ago": "{0} घंटे पहले",
    "{0} days ago": "{0} दिन पहले",
    "Live · checked {0} · next check in {1} min": "लाइव · {0} जाँचा गया · अगली जाँच {1} मिनट में",
    "Paused · last check {0}": "रुका हुआ · आख़िरी जाँच {0}",
    "Right now, for example": "अभी, उदाहरण के लिए",
    "This station <b>{0}</b> µg/m³ PM2.5 · the 4 stations around it <b>{1}</b>": "यह स्टेशन <b>{0}</b> µg/m³ PM2.5 · आस-पास के 4 स्टेशन <b>{1}</b>",
    "See why": "वजह देखें",
    "{0} says {1}": "{0} बताता है {1}",
    "That's its PM2.5 reading for the latest hour. On its own, there's no way to tell whether it's right.": "यह पिछले घंटे की उसकी PM2.5 रीडिंग है। अकेले इससे पता नहीं चलता कि यह सही है या नहीं।",
    "middle value": "बीच वाला मान",
    "Its four neighbours say {0}": "इसके चार पड़ोसी बताते हैं {0}",
    "We take the middle value of the four nearest monitors, within 12 km. One odd neighbour can't drag it.": "हम 12 km के अंदर के चार सबसे नज़दीकी मॉनिटरों का बीच वाला मान लेते हैं। एक अलग पड़ोसी इसे खींच नहीं सकता।",
    "For today, use": "आज के लिए इस्तेमाल करें",
    "It adds up, so use it": "आँकड़ा सही बैठता है, इसे इस्तेमाल करें",
    "{0}: use {1}": "{0}: {1} इस्तेमाल करें",
    "Before answering, we also check the reading against physics and against the monitor's own last three weeks. Every answer shows its evidence.":
      "जवाब देने से पहले हम रीडिंग को भौतिकी और मॉनिटर के अपने पिछले तीन हफ़्तों से भी जाँचते हैं। हर जवाब अपना सबूत दिखाता है।",
    "Its numbers add up against physics, its neighbours and its own past.": "इसके आँकड़े भौतिकी, पड़ोसियों और अपने पिछले रिकॉर्ड से मेल खाते हैं।",
    "Use its reading as it is.": "इसकी रीडिंग जैसी है वैसी इस्तेमाल करें।",
    "Something about it is unusual, but not clearly wrong.": "इसमें कुछ असामान्य है, पर साफ़ तौर पर ग़लत नहीं।",
    "Compare its reading with what its neighbours read before acting on it.": "फ़ैसला लेने से पहले इसकी रीडिंग की तुलना पड़ोसियों की रीडिंग से करें।",
    "Its numbers don't add up: impossible values, or far out of line with its neighbours or its past.": "इसके आँकड़े मेल नहीं खाते: असंभव मान, या पड़ोसियों या अपने पिछले रिकॉर्ड से बहुत अलग।",
    "Use what the four monitors around it read instead.": "इसकी जगह आस-पास के चार मॉनिटरों की रीडिंग इस्तेमाल करें।",
    "We can't check it right now: too few recent readings from it or its neighbours to run the checks.": "अभी हम इसे नहीं जाँच सकते: इससे या इसके पड़ोसियों से जाँच चलाने लायक हाल की रीडिंग बहुत कम हैं।",
    "Use what the four monitors around it read.": "आस-पास के चार मॉनिटरों की रीडिंग इस्तेमाल करें।",
    "What it means": "इसका मतलब",
    "What to do": "क्या करें",
    "Why it happens": "ऐसा क्यों होता है",
    "Almost always, the monitor stopped sending readings to the public feed (CPCB, through OpenAQ): a power cut, a network outage or maintenance. It isn't a fault in our checks. The <i>Live · checked … ago</i> pill at the top shows that our own hourly run is working.":
      "लगभग हमेशा, मॉनिटर ने सार्वजनिक फ़ीड (CPCB, OpenAQ के ज़रिए) पर रीडिंग भेजना बंद कर दिया: बिजली कटौती, नेटवर्क की दिक़्क़त या मरम्मत। यह हमारी जाँच की ग़लती नहीं है। सबसे ऊपर <i>लाइव · … जाँचा गया</i> वाला निशान दिखाता है कि हमारी अपनी हर घंटे की जाँच चल रही है।",
    "monitor right now": "मॉनिटर अभी",
    "monitors right now": "मॉनिटर अभी",
    ", for example:": ", उदाहरण के लिए:",
    "Right now: {0} reports impossible values in {1}% of last week's hours.": "अभी: {0} पिछले हफ़्ते के {1}% घंटों में असंभव मान दिखाता है।",
    "Right now: {0}. {1}": "अभी: {0}। {1}",
    "No monitor is raised by this check right now.": "अभी यह जाँच किसी मॉनिटर को नहीं उठा रही।",
    "PM10 (all dust)": "PM10 (कुल धूल)",
    "PM2.5 (fine dust)": "PM2.5 (बारीक धूल)",
    "NO2 (traffic gas)": "NO2 (ट्रैफ़िक गैस)",
    "Humidity": "नमी",
    "the limit": "सीमा",
    "impossible": "असंभव",
    "same as neighbours": "पड़ोसियों जितना",
    "3 weeks before": "3 हफ़्ते पहले",
    "last 7 days": "पिछले 7 दिन",
    "Physics": "भौतिकी",
    "Neighbours": "पड़ोसी",
    "History": "इतिहास",
    "Can this reading be real?": "क्या यह रीडिंग असली हो सकती है?",
    "Does it agree with the stations around it?": "क्या यह आस-पास के स्टेशनों से मेल खाता है?",
    "Has it suddenly changed?": "क्या यह अचानक बदल गया है?",
    "PM2.5 and PM10": "PM2.5 और PM10",
    "humidity": "नमी",
    "Raised by:": "किसने उठाया:",
    "A real local source, such as a busy junction, road dust, construction or burning within a few hundred metres, can also push one monitor away from neighbours 5–12 km off. Here, the monitor may be right.":
      "कुछ सौ मीटर के अंदर कोई असली स्थानीय स्रोत, जैसे व्यस्त चौराहा, सड़क की धूल, निर्माण या कुछ जलना, भी एक मॉनिटर को 5–12 km दूर के पड़ोसियों से अलग कर सकता है। ऐसे में मॉनिटर सही हो सकता है।",
    "Note:": "ध्यान दें:",
    "Copy link": "लिंक कॉपी करें",
    "Copied!": "कॉपी हो गया!",
    "Copy link to this monitor": "इस मॉनिटर का लिंक कॉपी करें",
    "Copy this link:": "यह लिंक कॉपी करें:",
    "OpenAQ location {0}": "OpenAQ location {0}",
    "This station, PM2.5 now": "यह स्टेशन, अभी PM2.5",
    "4 nearest stations, PM2.5 now": "4 नज़दीकी स्टेशन, अभी PM2.5",
    "India's 24-hour PM2.5 standard is {0} µg/m³.": "भारत का 24 घंटे का PM2.5 मानक {0} µg/m³ है।",
    " The four nearest stations read <b class=\"mono\">{0} µg/m³</b> PM2.5 right now.": " चार सबसे नज़दीकी स्टेशन अभी <b class=\"mono\">{0} µg/m³</b> PM2.5 पढ़ रहे हैं।",
    "{0} Its last answers are below, but they no longer describe the air now. Use what the stations around it read.{1}":
      "{0} इसके पिछले जवाब नीचे हैं, पर वे अब की हवा नहीं बताते। आस-पास के स्टेशनों की रीडिंग इस्तेमाल करें।{1}",
    "This station agrees with the stations around it. Its reading is a fair guide for this area.": "यह स्टेशन आस-पास के स्टेशनों से मेल खाता है। इस इलाक़े के लिए इसकी रीडिंग भरोसे लायक है।",
    "Something about this station is unusual. Before acting on its reading, compare it with the stations around it.{0}":
      "इस स्टेशन में कुछ असामान्य है। इसकी रीडिंग पर फ़ैसला लेने से पहले आस-पास के स्टेशनों से तुलना करें।{0}",
    "This station's numbers don't add up, and its neighbours have no reading right now either. Treat today's number with care.":
      "इस स्टेशन के आँकड़े मेल नहीं खाते, और अभी इसके पड़ोसियों की भी कोई रीडिंग नहीं है। आज के आँकड़े को सावधानी से लें।",
    "This station's numbers don't add up. For decisions today, use what the stations around it read.{0}":
      "इस स्टेशन के आँकड़े मेल नहीं खाते। आज के फ़ैसलों के लिए आस-पास के स्टेशनों की रीडिंग इस्तेमाल करें।{0}",
    "There isn't enough recent data to check this station.{0}": "इस स्टेशन को जाँचने के लिए हाल का पर्याप्त डेटा नहीं है।{0}",
    " Right now, though, it reads <b>{0}</b> the stations around it ({1} against {2} µg/m³).": " पर अभी यह आस-पास के स्टेशनों से <b>{0}</b> पढ़ रहा है ({2} के मुकाबले {1} µg/m³)।",
    "well above": "काफ़ी ऊपर",
    "well below": "काफ़ी नीचे",
    "The whole area rose together in the last few hours (this station {0}%, its neighbours {1}%), which is what smoke does, not what a broken monitor does.":
      "पिछले कुछ घंटों में पूरा इलाक़ा साथ-साथ बढ़ा (यह स्टेशन {0}%, इसके पड़ोसी {1}%), जो धुएँ से होता है, ख़राब मॉनिटर से नहीं।",
    "Air quality, 24-hour average · {0}": "हवा की गुणवत्ता, 24 घंटे का औसत · {0}",
    "this monitor": "यह मॉनिटर",
    "from the 4 monitors around it": "आस-पास के 4 मॉनिटरों से",
    "No reading in the last 4 weeks.": "पिछले 4 हफ़्तों में कोई रीडिंग नहीं।",
    "Last reading {0} IST, {1}": "आख़िरी रीडिंग {0} IST, {1}",
    "Hour by hour, against its neighbours": "घंटे-दर-घंटे, पड़ोसियों के मुकाबले",
    "Above zero: this station reads higher than the 4 nearest stations at that hour.": "शून्य से ऊपर: उस घंटे यह स्टेशन 4 सबसे नज़दीकी स्टेशनों से ज़्यादा पढ़ता है।",
    "Measure": "माप",
    "Loading the chart…": "चार्ट लोड हो रहा है…",
    "Last 7 days": "पिछले 7 दिन",
    "Last 28 days": "पिछले 28 दिन",
    "Show as table": "तालिका में देखें",
    "Hide table": "तालिका छिपाएँ",
    "Hour (IST)": "घंटा (IST)",
    "no data": "डेटा नहीं",
    "Last 48 hours: this station vs neighbours": "पिछले 48 घंटे: यह स्टेशन बनाम पड़ोसी",
    "PM2.5 µg/m³. Neighbour band is the range of the {0} nearest stations.": "PM2.5 µg/m³। धूसर पट्टी {0} सबसे नज़दीकी स्टेशनों की रेंज है।",
    "Compared with": "तुलना की गई",
    "All": "सभी",
    "No monitor matches. Try another name or area, or show all.": "कोई मॉनिटर नहीं मिला। दूसरा नाम या इलाक़ा आज़माएँ, या सभी दिखाएँ।",
    "No station matches": "कोई स्टेशन नहीं मिला",
    "Central Delhi": "मध्य दिल्ली",
    "North Delhi": "उत्तर दिल्ली",
    "South Delhi": "दक्षिण दिल्ली",
    "East Delhi": "पूर्वी दिल्ली",
    "West Delhi": "पश्चिमी दिल्ली",
    "Noida": "नोएडा",
    "Ghaziabad": "ग़ाज़ियाबाद",
    "Gurugram and Manesar": "गुरुग्राम और मानेसर",
    "Faridabad": "फ़रीदाबाद",
    "Bahadurgarh": "बहादुरगढ़",
    "Data is updating": "डेटा अपडेट हो रहा है",
    "We couldn't load the latest readings. Try again in a minute.": "ताज़ा रीडिंग लोड नहीं हो सकी। एक मिनट में फिर कोशिश करें।",
    "Try again": "फिर कोशिश करें",
    "Map view": "नक्शा",
    "List view": "सूची",
    "Play": "चलाएँ",
    "Pause": "रोकें",
    "Delhi": "दिल्ली",
    "{0} hours": "{0} घंटे",
    "{0} days": "{0} दिन",
    "The public feed from the monitors (CPCB, through OpenAQ) is {0} behind right now. Every answer here is for the newest hour it has: {1} IST.":
      "मॉनिटरों का सार्वजनिक फ़ीड (CPCB, OpenAQ के ज़रिए) अभी {0} पीछे चल रहा है। यहाँ हर जवाब उसके सबसे नए घंटे का है: {1} IST।",
    // the ?demo=1 tour
    "{0} air-quality monitors across Delhi and NCR, checked every hour.": "दिल्ली और NCR के {0} वायु-गुणवत्ता मॉनिटर, हर घंटे जाँचे जाते हैं।",
    "Delhi in 3D. Each mast is a monitor; its column is as tall as its PM2.5 reading, and the smog is thicker where the air is worse.":
      "3D में दिल्ली। हर खंभा एक मॉनिटर है; उसका स्तंभ उसकी PM2.5 रीडिंग जितना ऊँचा है, और जहाँ हवा ज़्यादा ख़राब है वहाँ धुंध घनी है।",
    "{0} reports readings that can't be real. Its numbers don't add up.": "{0} ऐसी रीडिंग भेजता है जो असली हो ही नहीं सकतीं। इसके आँकड़े मेल नहीं खाते।",
    "Anand Vihar, hour by hour, against the four stations around it. The shaded band is 11:00 to 17:00.": "आनंद विहार, घंटे-दर-घंटे, आस-पास के चार स्टेशनों के मुकाबले। रंगी हुई पट्टी 11:00 से 17:00 है।",
    "Jahangirpuri against its own last three weeks. Worth a look, not proof.": "जहाँगीरपुरी, अपने पिछले तीन हफ़्तों के मुकाबले। देखने लायक, पर सबूत नहीं।",
    "When a station is in doubt, use what the stations around it read right now.": "जब किसी स्टेशन पर शक हो, तो आस-पास के स्टेशनों की अभी की रीडिंग इस्तेमाल करें।",
    "A flag means the numbers don't add up. Not that anyone cheated.": "फ़्लैग का मतलब है कि आँकड़े मेल नहीं खाते। यह नहीं कि किसी ने धोखा दिया।",
    // the October 2025 illustration (spray3d.js)
    "Before": "पहले",
    "The monitor and the monitors around it agree: about 310 µg/m³ PM2.5.": "मॉनिटर और उसके आस-पास के मॉनिटर एक जैसा बताते हैं: लगभग 310 µg/m³ PM2.5।",
    "The tanker": "टैंकर",
    "A water tanker pulls up next to the monitor.": "पानी का एक टैंकर मॉनिटर के पास आकर रुकता है।",
    "The spray": "छिड़काव",
    "The spray settles the dust right at the monitor's inlet. Its reading falls to about 120.": "छिड़काव से धूल ठीक मॉनिटर के इनलेट पर बैठ जाती है। उसकी रीडिंग गिरकर लगभग 120 हो जाती है।",
    "The air": "हवा",
    "A few hundred metres away, nothing changed. The monitors there still read about 300.": "कुछ सौ मीटर दूर कुछ नहीं बदला। वहाँ के मॉनिटर अब भी लगभग 300 पढ़ते हैं।",
    "Ground Truth": "Ground Truth",
    "Ground Truth compares it with its neighbours. The numbers don't add up.": "Ground Truth इसकी तुलना पड़ोसियों से करता है। आँकड़े मेल नहीं खाते।",
  };

  // CPCB's own Hindi names for the AQI bands, and the advice line per band
  const BANDS = { Good: "अच्छा", Satisfactory: "संतोषजनक", Moderate: "मध्यम", Poor: "ख़राब", "Very poor": "बहुत ख़राब", Severe: "गंभीर" };
  const BAND_TODO = {
    Good: "बाहर की गतिविधियों के लिए अच्छा।",
    Satisfactory: "बाहर की गतिविधियाँ ठीक हैं। दमे वाले लोगों को थोड़ा असर लग सकता है।",
    Moderate: "बच्चे और दमे या दिल की बीमारी वाले लोग बाहर ज़्यादा मेहनत न करें।",
    Poor: "बाहर लंबी या भारी गतिविधि कम रखें, ख़ासकर बच्चों के लिए।",
    "Very poor": "बच्चों का बाहर खेलना कम रखें। असेंबली अंदर करें।",
    Severe: "बच्चों को अंदर रखें और बाहर कसरत न करें।",
  };

  // sentences the backend writes in English (scorer details, weather, fires)
  const updown = (s) => s === "about the same" ? "लगभग बराबर" : s.replace(/^(\d+)% higher$/, "$1% ज़्यादा").replace(/^(\d+)% lower$/, "$1% कम");
  const dirs = { north: "उत्तर", south: "दक्षिण", east: "पूर्व", west: "पश्चिम", "north-east": "उत्तर-पूर्व", "north-west": "उत्तर-पश्चिम", "south-east": "दक्षिण-पूर्व", "south-west": "दक्षिण-पश्चिम" };
  const dir = (d) => dirs[d] || d;
  const when = (w) => (w === "tonight" ? "आज रात" : "अभी");
  const DETAIL = [
    [/^([\d.]+)% of the last 7 days' hours report impossible values \(PM2\.5 above PM10, out of range, or a stuck sensor\)\.$/,
      (m, p) => `पिछले 7 दिनों के ${p}% घंटों में असंभव रीडिंग आई (PM2.5 का PM10 से ज़्यादा होना, सीमा से बाहर, या अटका हुआ सेंसर)।`],
    [/^Fewer than 24 hours of PM data in the last 7 days\.$/, () => "पिछले 7 दिनों में 24 घंटे से कम का PM डेटा।"],
    [/^Not enough recent data from this station or its neighbours\.$/, () => "इस स्टेशन या इसके पड़ोसियों से हाल का पर्याप्त डेटा नहीं।"],
    [/^Not enough days to compare against its own history\.$/, () => "अपने पिछले रिकॉर्ड से तुलना के लिए पर्याप्त दिन नहीं।"],
    [/^Against its neighbours, its daytime PM10 reads (.+?) than at night \((.+?) is typical for a station like it\)\.$/,
      (m, a, b) => `पड़ोसियों के मुकाबले, इसका दिन का PM10 रात से ${updown(a)} है (ऐसे स्टेशन के लिए ${updown(b)} सामान्य है)।`],
    [/^Against its neighbours, its daytime PM10 reads about the same as at night \((.+?) is typical for a station like it\)\.$/,
      (m, b) => `पड़ोसियों के मुकाबले, इसका दिन का PM10 रात जितना ही है (ऐसे स्टेशन के लिए ${updown(b)} सामान्य है)।`],
    [/^Its daytime PM10, against its neighbours, reads (.+?) than over its previous 3 weeks\.$/,
      (m, a) => `पड़ोसियों के मुकाबले इसका दिन का PM10 अपने पिछले 3 हफ़्तों से ${updown(a)} है।`],
    [/^Its daytime humidity, against its neighbours, reads ([\d.]+) pts (higher|lower) than over its previous 3 weeks\.$/,
      (m, n, hl) => `पड़ोसियों के मुकाबले इसकी दिन की नमी अपने पिछले 3 हफ़्तों से ${n} अंक ${hl === "higher" ? "ज़्यादा" : "कम"} है।`],
    [/^No reading since (\d\d):00 on (\d+) (\w+)\.$/, (m, h, d, mon) => `${d} ${mon}, ${h}:00 के बाद से कोई रीडिंग नहीं।`],
    [/^No reading in the last 4 weeks\.$/, () => "पिछले 4 हफ़्तों में कोई रीडिंग नहीं।"],
    [/^Calm air (right now|tonight) \(wind (\d+) km\/h\)( and the air is mixing only a few hundred metres up)?: pollution is building up across the city\.$/,
      (m, w, k, low) => `${when(w)} हवा थमी है (हवा ${k} km/h)${low ? " और हवा सिर्फ़ कुछ सौ मीटर ऊपर तक मिल रही है" : ""}: पूरे शहर में प्रदूषण जमा हो रहा है।`],
    [/^A light wind from the ([\w-]+) (right now|tonight) \((\d+) km\/h\): the air is moving a little, so readings drift together\.$/,
      (m, d, w, k) => `${when(w)} ${dir(d)} से हल्की हवा (${k} km/h): हवा थोड़ी चल रही है, इसलिए रीडिंग साथ-साथ बदलती हैं।`],
    [/^Wind from the ([\w-]+) at (\d+) km\/h (right now|tonight): the air is being cleared across the city, so every monitor falls together\.$/,
      (m, d, k, w) => `${when(w)} ${dir(d)} से ${k} km/h की हवा: पूरे शहर की हवा साफ़ हो रही है, इसलिए हर मॉनिटर साथ-साथ गिरता है।`],
    [/^No farm fires seen in the last 24 h to the north-west\.$/, () => "पिछले 24 घंटों में उत्तर-पश्चिम में खेतों में कोई आग नहीं दिखी।"],
    [/^(\d+) farm fires? in the last 24 h, ([\w-]+) of the city\.$/, (m, n, d) => `पिछले 24 घंटों में शहर के ${dir(d)} में खेतों में ${n} जगह आग।`],
  ];

  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const fill = (tpl, vals) => tpl.replace(/\{(\d+)\}/g, (m, i) => vals[i]);

  // tr`Last reading ${when} IST` -> the Hindi template, values in place; English unless Hindi is on
  function tr(strings, ...vals) {
    const key = strings.reduce((a, s, i) => a + (i ? `{${i - 1}}` : "") + s, "");
    return fill(lang === "hi" && UI[key] != null ? UI[key] : key, vals);
  }
  const t = (s) => (lang === "hi" && UI[s] != null ? UI[s] : s);
  function detail(s) {
    if (lang !== "hi" || !s) return s;
    for (const [re, f] of DETAIL) { const m = s.match(re); if (m) return f(...m); }
    return s;
  }

  // swap every page block whose English text is in PAGE; a block holding ids, controls or pills it doesn't
  // carry over is left alone, and its children are tried instead
  const SEL = "title, h1, h2, h3, h4, p, li, summary, figcaption, th, td, dt, dd, nav a, footer a, .label, button, .stat span, .pipe span, a.btn, a.tour-link, label, .sp-tag .who";
  function page(root = document) {
    if (lang !== "hi") return;
    for (const el of root.querySelectorAll(SEL)) {
      if (!el.isConnected) continue;
      const hi = PAGE[norm(el.textContent)];
      if (hi == null) continue;
      const kept = [...el.querySelectorAll("[id], button, input, select, textarea")].every((c) => c.id && hi.includes(`id="${c.id}"`));
      if (kept) el.innerHTML = hi;
    }
  }

  window.GT_I18N = { lang, tr, t, detail, page, band: (b) => (lang === "hi" && BANDS[b]) || b, bandTodo: (b, en) => (lang === "hi" && BAND_TODO[b]) || en, PAGE };
})();
