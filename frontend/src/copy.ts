// Interface wording only. Plan text, warnings and the disclaimer come from the API, never from here.
import type { Lang } from "@brand";
import type { Budget, FieldKey, TableKey, Year } from "./api";

type Field = { label: string; unit: string; hint?: string };

type Copy = {
  brand: string; brand2: string; otherLang: string; title: string; intro: string;
  step1: string; gov: string; budget: string; year: string; yearHint: string; step2: string; step3: string;
  rain: string; grey: string; materials: string; colItem: string; colQty: string; colWhy: string; total: string; jod: string;
  pricesNote: string; plants: string; safety: string; print: string; download: string; details: string;
  loading: string; offline: string; retry: string; none: string;
  fields: Record<FieldKey, Field>;
  budgets: Record<Budget, [string, string]>;
  years: Record<Year, string>;
  results: Record<"jod" | "trips" | "water" | "pay", [string, string]>;
  range: (lo: number, hi: number) => string;
  line: (gov: string, mm: string, roof: string, people: string) => string;
  estimateNote: (year: string) => string;
  detailLines: (v: Record<string, string>) => string[];
  // impact
  impact: string; tankChart: string; tankLegend: [string, string]; demandChart: string; fromRain: string; bought: string;
  chartSummary: (dry: string, overflow: string, used: string, potential: string) => string;
  sareef: string; sareefSub: string; today: string; withSystem: string;
  sareefRows: Record<"trips" | "jod" | "co2", [string, string]>;
  community: string; homes: string; communityLine: (homes: string, water: string, trips: string, co2: string) => string;
  // AI plan
  aiTitle: string; aiIntro: string; model: string; aiButton: string; aiCancel: string; aiWorking: (m: string) => string;
  noModels: string; byModel: (m: string) => string; byTemplate: string; fallback: (m: string) => string;
  useTemplate: string; stale: string; failDetails: string;
  checksLabel: string; of: string; checkRules: Record<string, string>;
  // method
  method: string; who: string; whoRows: [string, string][]; rules: string; banned: string; allowed: string;
  retries: (n: number, lo: number, hi: number) => string; formulas: string; formulaLines: string[];
  schema: string; modelHeading: string; modelLine: (m: string, url: string) => string; modelNone: string; prompt: string;
  cloudNote: string; cloudLine: (m: string) => string; cloudTag: string; paybackNote: (c: string) => string;
  // assumptions
  data: string; dataIntro: (v: number, n: number) => string; tables: Record<TableKey, string>;
  columns: Record<string, string>; govNames: Record<string, string>;
};

const FORMULAS = [
  "V_year = A × R × C",
  "I_m = A × (R × s_m × k) × C × (1 − f)",
  "L_m = min(K, max(0, L_m−1 + I_m − D_m))",
  "G_week = (P × n_shower × l_shower + n_laundry × l_laundry + P × l_sink) × r",
  "Trips = W × s ÷ T",
  "JOD = Trips × p_trip + W × (1 − s) × p_tariff",
  "CO₂ = Trips × d_trip × e_diesel + W × E_pump × e_grid",
  "Payback = 12 × Cost ÷ JOD",
];

export const COPY: Record<Lang, Copy> = {
  en: {
    brand: "Ramadi-Cycle", brand2: "رمادي", otherLang: "العربية",
    title: "How much water and money can your home save?",
    intro: "Type in a few facts about your home. The numbers and the build plan below update straight away.",
    step1: "About your home", gov: "Where do you live?", budget: "How much do you want to spend?",
    year: "What kind of rain year?", yearHint: "Dry and wet years show the range you might see.",
    step2: "What you save each year", step3: "Your build plan",
    rain: "Collect rainwater from the roof", grey: "Reuse shower and laundry water",
    materials: "What to buy", colItem: "Item", colQty: "Qty", colWhy: "Why", total: "Total cost", jod: "JOD",
    pricesNote: "Prices are estimates. Ask a local shop for a quote.",
    plants: "Trees you can water with shower water", safety: "Safety rules. Please read.",
    print: "Print the plan", download: "Save the plan", details: "How we calculated this",
    loading: "Calculating…", offline: "The calculator isn't running. Start it with this command, then try again:",
    retry: "Try again", none: "—",
    fields: {
      roof_m2: { label: "Roof size", unit: "m²", hint: "Length × width of the flat roof. A typical house is 100 to 150." },
      people: { label: "People living in the home", unit: "people" },
      showers_pp: { label: "Showers per person each week", unit: "showers" },
      laundry_loads: { label: "Washing-machine loads each week", unit: "loads" },
      capacity_m3: { label: "Rain tank size you can fit", unit: "m³", hint: "1 m³ = 1,000 litres. Most homes fit 1 to 3." },
    },
    budgets: { low: ["Low cost", "Do it yourself, {c} JOD"], full: ["Full system", "With pump, fitted by a plumber, {c} JOD"] },
    years: { dry: "Dry", average: "Average", wet: "Wet" },
    results: {
      jod: ["Money saved", "JOD a year"], trips: ["Fewer tanker trips", "trips a year"],
      water: ["Water reused", "m³ a year"], pay: ["The system pays for itself in", "months"],
    },
    range: (lo, hi) => `Enter a number from ${lo} to ${hi}. Using the nearest one.`,
    line: (g, mm, r, p) => `${g}: about ${mm} mm of rain a year · ${r} m² roof · ${p} people`,
    estimateNote: (y) => `Estimates for a ${y.toLowerCase()} rain year. Drinking and cooking water are not included.`,
    detailLines: (v) => [
      `Rain used: ${v.rainUsed} m³ · greywater: ${v.grey} m³`,
      `CO₂ cut: ${v.co2} kg a year`,
      `We assumed a ${v.tankerVolume} m³ tanker at ${v.tankerPrice} JOD and ${v.litres} litres per person a day for cleaning and toilet flushing. All of these are estimates and unverified.`,
    ],
    impact: "Through the year",
    tankChart: "Rain tank level by month (m³)", tankLegend: ["Tank level", "Tank size"],
    demandChart: "Flushing and cleaning water: from rain or still bought (m³)", fromRain: "From rain", bought: "Still bought",
    chartSummary: (d, o, u, p) => `The tank runs dry in ${d} of 12 months. ${o} m³ overflows in winter. ${u} of the ${p} m³ your roof can catch gets used. The tank starts empty in January.`,
    sareef: "Sareef counter", sareefSub: "Water for flushing, cleaning and the garden. Drinking and cooking water don't change.",
    today: "Today", withSystem: "With Ramadi-Cycle",
    sareefRows: { trips: ["Tanker trips", "a year"], jod: ["Spent on this water", "JOD a year"], co2: ["CO₂", "kg a year"] },
    community: "If your neighbourhood did it", homes: "Homes",
    communityLine: (h, w, t, c) => `${h} homes would reuse ${w} m³ of water, avoid ${t} tanker trips and cut ${c} tonnes of CO₂ a year.`,
    aiTitle: "Write the plan with AI", aiIntro: "A model running on this laptop picks parts from the catalogue and writes the steps. Code checks every answer before you see it.",
    model: "Model", aiButton: "Write my plan", aiCancel: "Cancel", aiWorking: (m) => `Writing your plan with ${m}. This can take a few minutes on a laptop.`,
    noModels: "No model found, so you're seeing the built-in plan. To use AI, install Ollama and run: ollama pull qwen3:4b",
    byModel: (m) => `Written on this laptop by ${m}. Prices and safety checks come from code, not the model.`,
    byTemplate: "Built-in plan for your budget.",
    fallback: (m) => `${m} couldn't write a plan that passed the checks, so this is the built-in plan.`,
    useTemplate: "Back to the built-in plan", stale: "You changed your home details, so the AI plan was cleared.",
    failDetails: "What went wrong",
    checksLabel: "Safety checks passed", of: "of",
    checkRules: {},
    method: "Safety and method", who: "Who does what",
    whoRows: [["Rainfall, water balance, trips, JOD, CO₂, payback", "Python engine"], ["Prices and quantity limits", "catalog.csv"],
      ["Safety warnings and banned words", "Fixed in code"], ["Choosing parts, ordering steps, explaining why", "Local model"],
      ["Rejecting invalid or unsafe answers", "Validation code"]],
    rules: "Fixed safety rules", banned: "Model text is rejected if it contains", allowed: "Allowed phrases",
    retries: (n, lo, hi) => `Quantities must be ${lo} to ${hi}. After ${n} failed tries the built-in plan is used.`,
    formulas: "Formulas", formulaLines: FORMULAS, schema: "Answer format the model must follow",
    modelHeading: "Model", modelLine: (m, url) => `${m} through Ollama at ${url}. Nothing leaves this laptop.`,
    cloudNote: "This is a cloud model. Your home's numbers and the instructions are sent to OpenRouter. Pick a local model to keep everything on this laptop.",
    cloudLine: (m) => `${m} on OpenRouter. Your home's numbers and the instructions leave this laptop.`, cloudTag: "cloud",
    paybackNote: (c) => `Payback uses the standard parts list (${c} JOD), so it doesn't change with the AI's choices.`,
    modelNone: "No model running. Built-in plan only.", prompt: "Instructions sent to the model",
    data: "Assumptions and sources",
    dataIntro: (v, n) => `Every number the calculator uses, with its source. ${v} of ${n} have a published source so far. Fix one with a pull request to data/.`,
    tables: { assumptions: "Assumptions", rainfall: "Rainfall by governorate", monthly_share: "Rain by month", catalog: "Parts and prices", plants: "Plants" },
    columns: {},
    govNames: {},
  },
  ar: {
    brand: "رمادي", brand2: "Ramadi-Cycle", otherLang: "English",
    title: "كم يوفّر بيتك من الماء والمال؟",
    intro: "اكتب بعض المعلومات عن بيتك، وستظهر الأرقام وخطة التنفيذ في الأسفل مباشرة.",
    step1: "معلومات البيت", gov: "أين تسكن؟", budget: "كم تريد أن تصرف؟",
    year: "أي نوع من السنوات المطرية؟", yearHint: "السنة الجافة والماطرة تبيّن المدى المتوقع.",
    step2: "ما توفّره كل سنة", step3: "خطة التنفيذ",
    rain: "جمع مياه الأمطار من السطح", grey: "إعادة استخدام مياه الدوش والغسالة",
    materials: "ماذا تشتري", colItem: "البند", colQty: "الكمية", colWhy: "السبب", total: "التكلفة الكاملة", jod: "دينار",
    pricesNote: "الأسعار تقديرية. اسأل محلاً قريباً عن السعر.",
    plants: "أشجار يمكن سقيها بمياه الدوش", safety: "قواعد السلامة. اقرأها من فضلك.",
    print: "اطبع الخطة", download: "احفظ الخطة", details: "كيف حسبنا هذه الأرقام",
    loading: "جارٍ الحساب…", offline: "الحاسبة غير مشغّلة. شغّلها بهذا الأمر ثم حاول مجدداً:",
    retry: "حاول مجدداً", none: "—",
    fields: {
      roof_m2: { label: "مساحة السطح", unit: "م²", hint: "الطول × العرض للسطح. البيت العادي بين 100 و150." },
      people: { label: "عدد أفراد البيت", unit: "شخص" },
      showers_pp: { label: "عدد مرات الدوش لكل شخص في الأسبوع", unit: "مرة" },
      laundry_loads: { label: "عدد غسلات الغسالة في الأسبوع", unit: "غسلة" },
      capacity_m3: { label: "حجم خزان المطر الذي تستطيع وضعه", unit: "م³", hint: "1 م³ = 1000 لتر. أغلب البيوت تتسع لـ 1 إلى 3." },
    },
    budgets: { low: ["تكلفة قليلة", "تركّبه بنفسك، {c} دينار"], full: ["نظام كامل", "مع مضخة، يركّبه سبّاك، {c} دينار"] },
    years: { dry: "جافة", average: "متوسطة", wet: "ماطرة" },
    results: {
      jod: ["المال الموفّر", "دينار بالسنة"], trips: ["رحلات صهريج أقل", "رحلة بالسنة"],
      water: ["مياه يعاد استخدامها", "م³ بالسنة"], pay: ["يسترد النظام تكلفته خلال", "شهر"],
    },
    range: (lo, hi) => `أدخل رقماً من ${lo} إلى ${hi}. نستخدم أقرب رقم مسموح.`,
    line: (g, mm, r, p) => `${g}: حوالي ${mm} ملم مطر بالسنة · سطح ${r} م² · ${p} أشخاص`,
    estimateNote: (y) => `تقديرات لسنة أمطار ${y}. لا تشمل مياه الشرب والطبخ.`,
    detailLines: (v) => [
      `مياه أمطار مستخدمة: ${v.rainUsed} م³ · مياه رمادية: ${v.grey} م³`,
      `ثاني أكسيد الكربون الموفّر: ${v.co2} كغ بالسنة`,
      `افترضنا: صهريج ${v.tankerVolume} م³ بسعر ${v.tankerPrice} دينار، و${v.litres} لتراً للشخص يومياً للتنظيف وصناديق الطرد. كل هذه الأرقام تقديرية وغير متحقق منها.`,
    ],
    impact: "خلال السنة",
    tankChart: "مستوى خزان المطر شهرياً (م³)", tankLegend: ["مستوى الخزان", "سعة الخزان"],
    demandChart: "مياه الطرد والتنظيف: من المطر أم ما زالت تُشترى (م³)", fromRain: "من المطر", bought: "ما زالت تُشترى",
    chartSummary: (d, o, u, p) => `يجف الخزان في ${d} من 12 شهراً. يفيض ${o} م³ في الشتاء. يُستخدم ${u} من أصل ${p} م³ يمكن لسطحك جمعها. يبدأ الخزان فارغاً في كانون الثاني.`,
    sareef: "عدّاد الصهريج", sareefSub: "مياه الطرد والتنظيف والحديقة. مياه الشرب والطبخ لا تتغير.",
    today: "اليوم", withSystem: "مع رمادي",
    sareefRows: { trips: ["رحلات الصهريج", "بالسنة"], jod: ["المصروف على هذه المياه", "دينار بالسنة"], co2: ["ثاني أكسيد الكربون", "كغ بالسنة"] },
    community: "لو طبّقه الحي كله", homes: "عدد البيوت",
    communityLine: (h, w, t, c) => `${h} بيتاً ستعيد استخدام ${w} م³ من المياه، وتوفّر ${t} رحلة صهريج، وتخفض ${c} طناً من ثاني أكسيد الكربون كل سنة.`,
    aiTitle: "اكتب الخطة بالذكاء الاصطناعي", aiIntro: "نموذج يعمل على هذا الجهاز يختار المواد من القائمة ويكتب الخطوات. يفحص الكود كل إجابة قبل أن تراها.",
    model: "النموذج", aiButton: "اكتب خطتي", aiCancel: "إلغاء", aiWorking: (m) => `جارٍ كتابة خطتك بواسطة ${m}. قد يستغرق ذلك بضع دقائق على جهاز محمول.`,
    noModels: "لم يُعثر على نموذج محلي، لذا تظهر الخطة الجاهزة. لاستخدام الذكاء الاصطناعي ثبّت Ollama ثم شغّل: ollama pull qwen3:4b",
    byModel: (m) => `كتبها ${m} على هذا الجهاز. الأسعار وفحوص السلامة من الكود وليست من النموذج.`,
    byTemplate: "الخطة الجاهزة لميزانيتك.",
    fallback: (m) => `لم يستطع ${m} كتابة خطة تجتاز الفحوص، لذا تظهر الخطة الجاهزة.`,
    useTemplate: "ارجع إلى الخطة الجاهزة", stale: "غيّرت معلومات البيت، فحُذفت خطة الذكاء الاصطناعي.",
    failDetails: "ما الذي حدث",
    checksLabel: "اجتازت الخطة فحوص السلامة", of: "من",
    checkRules: {
      "All item and plant IDs exist in the tables": "كل المواد والنباتات موجودة في الجداول",
      "Quantities within 1 to 50": "الكميات بين 1 و50",
      "No banned terms in generated text": "لا كلمات محظورة في النص",
      "First-flush diverter included": "محوّل الدفقة الأولى موجود",
      "Non-potable labels included": "ملصقات «غير صالحة للشرب» موجودة",
      "Fixed warnings and disclaimer attached": "التحذيرات الثابتة وإخلاء المسؤولية مرفقة",
    },
    method: "السلامة وطريقة الحساب", who: "من يفعل ماذا",
    whoRows: [["المطر وموازنة المياه والرحلات والدنانير وثاني أكسيد الكربون والاسترداد", "محرّك Python"], ["الأسعار وحدود الكميات", "catalog.csv"],
      ["تحذيرات السلامة والكلمات المحظورة", "ثابتة في الكود"], ["اختيار المواد وترتيب الخطوات وشرح السبب", "النموذج المحلي"],
      ["رفض الإجابات غير الصالحة أو غير الآمنة", "كود التحقق"]],
    rules: "قواعد السلامة الثابتة", banned: "يُرفض نص النموذج إذا احتوى على", allowed: "عبارات مسموحة",
    retries: (n, lo, hi) => `يجب أن تكون الكميات بين ${lo} و${hi}. بعد ${n} محاولات فاشلة تُستخدم الخطة الجاهزة.`,
    formulas: "المعادلات", formulaLines: FORMULAS, schema: "صيغة الإجابة التي يلتزم بها النموذج",
    modelHeading: "النموذج", modelLine: (m, url) => `${m} عبر Ollama على ${url}. لا يغادر أي شيء هذا الجهاز.`,
    cloudNote: "هذا نموذج سحابي. تُرسل أرقام بيتك والتعليمات إلى OpenRouter. اختر نموذجاً محلياً ليبقى كل شيء على هذا الجهاز.",
    cloudLine: (m) => `${m} على OpenRouter. تغادر أرقام بيتك والتعليمات هذا الجهاز.`, cloudTag: "سحابي",
    paybackNote: (c) => `مدة الاسترداد محسوبة على قائمة المواد القياسية (${c} دينار)، فلا تتغير باختيارات الذكاء الاصطناعي.`,
    modelNone: "لا يوجد نموذج مشغّل. الخطة الجاهزة فقط.", prompt: "التعليمات المرسلة إلى النموذج",
    data: "الافتراضات والمصادر",
    dataIntro: (v, n) => `كل رقم تستخدمه الحاسبة مع مصدره. لـ ${v} من ${n} مصدر منشور حتى الآن. صحّح أي رقم بطلب دمج إلى data/.`,
    tables: { assumptions: "الافتراضات", rainfall: "الأمطار حسب المحافظة", monthly_share: "المطر حسب الشهر", catalog: "المواد والأسعار", plants: "النباتات" },
    columns: {
      parameter: "المعامل", value: "القيمة", unit: "الوحدة", source: "المصدر", status: "الحالة", governorate: "المحافظة",
      annual_mm: "ملم بالسنة", month: "الشهر", share_of_annual_rain: "نسبة المطر السنوي", item_id: "الرمز", name_en: "الاسم (إنجليزي)",
      name_ar: "الاسم", category: "الفئة", price_jod: "السعر (دينار)", budget_level: "الميزانية", plant_id: "الرمز",
      greywater_ok: "مناسب للمياه الرمادية", note: "ملاحظة",
    },
    govNames: {
      "Amman (west)": "عمّان (الغربية)", "Amman (east)": "عمّان (الشرقية)", Zarqa: "الزرقاء", Irbid: "إربد", Ajloun: "عجلون",
      Jerash: "جرش", "Balqa (Salt)": "البلقاء (السلط)", Madaba: "مأدبا", Mafraq: "المفرق", Karak: "الكرك", Tafilah: "الطفيلة",
      "Ma'an": "معان", Aqaba: "العقبة",
    },
  },
};

// ---------------------------------------------------------------- pages, navigation and landing

type PageCopy = {
  nav: Record<"home" | "dashboard" | "plan" | "method" | "data", string>;
  skip: string; menu: string;
  steps: [string, string, string]; stepLabel: string;
  landing: {
    eyebrow: string; title: string; sub: string; cta: string; ctaSecondary: string;
    previewLabel: string; previewYours: string; previewExample: string;
    problemTitle: string; problems: [string, string][]; problemNote: string;
    howTitle: string; how: [string, string][];
    getTitle: string; get: [string, string][];
    trustTitle: string; trust: [string, string][];
    finalTitle: string; finalSub: string;
    diagram: { roof: string; tank: string; trees: string; tap: string };
  };
  setup: {
    title: string; sub: string; where: string; roofTank: string; household: string; spend: string;
    live: string; liveSub: string; next: string; saved: string;
  };
  dash: {
    title: string; edit: string; co2: string; planTitle: string; planCost: string; planSteps: (n: number) => string;
    planCta: string; dataTitle: string; dataBody: (v: number, n: number) => string; dataCta: string;
    noData: string; firstVisit: string; firstCta: string;
  };
  planPage: { title: string; back: string };
  methodPage: { title: string; sub: string };
  dataPage: { title: string };
  footer: { open: string; offline: string };
};

export const PAGES: Record<Lang, PageCopy> = {
  en: {
    nav: { home: "Your home", dashboard: "Savings", plan: "Build plan", method: "How it works", data: "Data" },
    skip: "Skip to content", menu: "Main",
    steps: ["Your home", "Your savings", "Your build plan"], stepLabel: "Step",
    landing: {
      eyebrow: "For homes in Jordan · Free · Works offline",
      title: "Turn the rain on your roof into fewer tanker trips.",
      sub: "See how much water, money and diesel your home can save by collecting rain and reusing shower water. Then get a priced, safety-checked plan you can hand to a plumber.",
      cta: "Check my home", ctaSecondary: "How it works",
      previewLabel: "What a home like yours saves", previewYours: "Based on the details you entered", previewExample: "Example: 120 m² roof, 5 people, 2 m³ tank",
      problemTitle: "Water reaches most homes about once a week",
      problems: [["1 day a week", "Municipal water fills the roof tank about once a week."], ["20–30 JOD", "What families pay for one tanker load when the tank runs dry."], ["Lost twice", "Winter rain runs off the roof into the street, and shower water goes to the sewer."]],
      problemNote: "Figures from the team brief. Not yet checked against a primary source.",
      howTitle: "Three steps, about five minutes",
      how: [["Tell us about your home", "Where you live, your roof, your tank and how many people live there."], ["See what you save", "Tanker trips, dinars and CO₂ each year, with the tank month by month."], ["Get your build plan", "Steps, a priced parts list and safety rules, in Arabic or English."]],
      getTitle: "What you get",
      get: [["A year of your tank", "Month-by-month water balance: when it fills, overflows and runs dry."], ["The Sareef counter", "Tanker trips, dinars and CO₂ today versus with the system."], ["A plan a plumber can price", "Parts from a local catalogue with quantities and prices."], ["Safety built in", "Fixed greywater rules and a first-flush diverter in every plan."]],
      trustTitle: "Built so you can trust the numbers",
      trust: [["Runs on this laptop", "No cloud, no account, no personal data. It works with Wi-Fi off."], ["Every number has a source", "Each assumption is listed with its source and whether it's verified."], ["AI checked by code", "A local model writes the plan. Code sets every price and rejects unsafe answers."], ["Open source", "MIT licence. The data lives in CSV files anyone can correct."]],
      finalTitle: "Ready to see your home's numbers?", finalSub: "It takes about two minutes. Nothing leaves this computer.",
      diagram: { roof: "Roof", tank: "Rain tank", trees: "Trees", tap: "Flushing" },
    },
    setup: {
      title: "Tell us about your home", sub: "Your numbers update as you type. You can change anything later.",
      where: "Where you live", roofTank: "Roof and tank", household: "Who lives there", spend: "Budget",
      live: "Live estimate", liveSub: "Updates as you type", next: "See my savings", saved: "Saved on this computer only.",
    },
    dash: {
      title: "Your savings", edit: "Edit home details", co2: "CO₂ cut",
      planTitle: "Your build plan", planCost: "Parts cost", planSteps: (n) => `${n} build steps`, planCta: "Open build plan",
      dataTitle: "How sure are these numbers?", dataBody: (v, n) => `${v} of ${n} assumptions have a published source. The rest are placeholders until someone finds one.`,
      dataCta: "See every assumption", noData: "Waiting for the calculator…",
      firstVisit: "These numbers use example details.", firstCta: "Enter your home",
    },
    planPage: { title: "Your build plan", back: "Back to savings" },
    methodPage: { title: "How it works", sub: "Python calculates every number, price and safety rule. A local model only picks parts and writes the steps, and code checks its answer." },
    dataPage: { title: "Data and sources" },
    footer: { open: "Open source · MIT", offline: "Runs on this computer. No data leaves it." },
  },
  ar: {
    nav: { home: "بيتك", dashboard: "التوفير", plan: "خطة التنفيذ", method: "كيف يعمل", data: "البيانات" },
    skip: "انتقل إلى المحتوى", menu: "القائمة الرئيسية",
    steps: ["بيتك", "ما توفّره", "خطة التنفيذ"], stepLabel: "الخطوة",
    landing: {
      eyebrow: "لبيوت الأردن · مجاني · يعمل دون إنترنت",
      title: "حوّل مطر سطحك إلى رحلات صهريج أقل.",
      sub: "اعرف كم يوفّر بيتك من الماء والمال والديزل بجمع مياه المطر وإعادة استخدام مياه الدوش، ثم احصل على خطة مسعّرة ومفحوصة السلامة تسلّمها للسبّاك.",
      cta: "افحص بيتي", ctaSecondary: "كيف يعمل",
      previewLabel: "ما يوفّره بيت مثل بيتك", previewYours: "بناءً على المعلومات التي أدخلتها", previewExample: "مثال: سطح 120 م²، 5 أشخاص، خزان 2 م³",
      problemTitle: "تصل المياه إلى أغلب البيوت مرة في الأسبوع",
      problems: [["يوم في الأسبوع", "تملأ مياه البلدية خزان السطح مرة في الأسبوع تقريباً."], ["20–30 ديناراً", "ما تدفعه الأسرة ثمناً لصهريج واحد عندما يفرغ الخزان."], ["ضياع مرتين", "مطر الشتاء يسيل من السطح إلى الشارع، ومياه الدوش تذهب إلى المجاري."]],
      problemNote: "أرقام من ملخص الفريق، لم يُتحقق منها من مصدر أولي بعد.",
      howTitle: "ثلاث خطوات في نحو خمس دقائق",
      how: [["أخبرنا عن بيتك", "مكان سكنك وسطحك وخزانك وعدد أفراد البيت."], ["اعرف ما توفّره", "رحلات الصهريج والدنانير وثاني أكسيد الكربون كل سنة، مع الخزان شهراً بشهر."], ["احصل على خطة التنفيذ", "خطوات وقائمة مواد مسعّرة وقواعد سلامة، بالعربية أو الإنجليزية."]],
      getTitle: "ماذا تحصل",
      get: [["سنة كاملة لخزانك", "موازنة المياه شهراً بشهر: متى يمتلئ ومتى يفيض ومتى يجف."], ["عدّاد الصهريج", "رحلات الصهريج والدنانير وثاني أكسيد الكربون اليوم ومع النظام."], ["خطة يستطيع السبّاك تسعيرها", "مواد من قائمة محلية بالكميات والأسعار."], ["السلامة جزء من الخطة", "قواعد ثابتة للمياه الرمادية ومحوّل الدفقة الأولى في كل خطة."]],
      trustTitle: "مصمم لتثق بالأرقام",
      trust: [["يعمل على هذا الجهاز", "لا سحابة ولا حساب ولا بيانات شخصية. يعمل والإنترنت مطفأ."], ["لكل رقم مصدر", "كل افتراض مذكور مع مصدره وهل تم التحقق منه."], ["الذكاء الاصطناعي يفحصه الكود", "نموذج محلي يكتب الخطة، والكود يحدد الأسعار ويرفض الإجابات غير الآمنة."], ["مفتوح المصدر", "رخصة MIT. البيانات في ملفات CSV يستطيع أي شخص تصحيحها."]],
      finalTitle: "جاهز لترى أرقام بيتك؟", finalSub: "يستغرق نحو دقيقتين. لا يغادر أي شيء هذا الجهاز.",
      diagram: { roof: "السطح", tank: "خزان المطر", trees: "الأشجار", tap: "صناديق الطرد" },
    },
    setup: {
      title: "أخبرنا عن بيتك", sub: "تتحدث الأرقام أثناء الكتابة. يمكنك تغيير أي شيء لاحقاً.",
      where: "مكان السكن", roofTank: "السطح والخزان", household: "من يسكن البيت", spend: "الميزانية",
      live: "تقدير مباشر", liveSub: "يتحدث أثناء الكتابة", next: "اعرض ما أوفّره", saved: "محفوظ على هذا الجهاز فقط.",
    },
    dash: {
      title: "ما توفّره", edit: "عدّل معلومات البيت", co2: "خفض ثاني أكسيد الكربون",
      planTitle: "خطة التنفيذ", planCost: "تكلفة المواد", planSteps: (n) => `${n} خطوات تنفيذ`, planCta: "افتح خطة التنفيذ",
      dataTitle: "ما مدى دقة هذه الأرقام؟", dataBody: (v, n) => `لـ ${v} من ${n} افتراضاً مصدر منشور. البقية مؤقتة حتى يجد أحد مصدراً لها.`,
      dataCta: "اعرض كل الافتراضات", noData: "بانتظار الحاسبة…",
      firstVisit: "هذه الأرقام مبنية على معلومات توضيحية.", firstCta: "أدخل معلومات بيتك",
    },
    planPage: { title: "خطة التنفيذ", back: "ارجع إلى التوفير" },
    methodPage: { title: "كيف يعمل", sub: "يحسب Python كل رقم وسعر وقاعدة سلامة. النموذج المحلي يختار المواد ويكتب الخطوات فقط، والكود يفحص إجابته." },
    dataPage: { title: "البيانات والمصادر" },
    footer: { open: "مفتوح المصدر · MIT", offline: "يعمل على هذا الجهاز. لا تغادره أي بيانات." },
  },
};
