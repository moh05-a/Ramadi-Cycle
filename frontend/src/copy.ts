// Interface wording only. Plan text, warnings and the disclaimer come from the API, never from here.
import type { Lang } from "@brand";
import type { Budget, FieldKey } from "./api";

type Field = { label: string; unit: string; hint?: string };

type Copy = {
  brand: string; brand2: string; otherLang: string; title: string; intro: string;
  step1: string; gov: string; budget: string; step2: string; step3: string;
  rain: string; grey: string; materials: string; colItem: string; colQty: string; total: string; jod: string;
  pricesNote: string; plants: string; safety: string; print: string; download: string; details: string;
  estimateNote: string; loading: string; offline: string; retry: string; none: string;
  fields: Record<FieldKey, Field>;
  budgets: Record<Budget, [string, string]>;
  results: Record<"jod" | "trips" | "water" | "pay", [string, string]>;
  range: (lo: number, hi: number) => string;
  line: (gov: string, mm: string, roof: string, people: string) => string;
  detailLines: (v: Record<string, string>) => string[];
};

export const COPY: Record<Lang, Copy> = {
  en: {
    brand: "Ramadi-Cycle", brand2: "رمادي", otherLang: "العربية",
    title: "How much water and money can your home save?",
    intro: "Type in a few facts about your home. The numbers and the build plan below update straight away.",
    step1: "About your home", gov: "Where do you live?", budget: "How much do you want to spend?",
    step2: "What you save each year", step3: "Your build plan",
    rain: "Collect rainwater from the roof", grey: "Reuse shower and laundry water",
    materials: "What to buy", colItem: "Item", colQty: "Qty", total: "Total cost", jod: "JOD",
    pricesNote: "Prices are estimates. Ask a local shop for a quote.",
    plants: "Trees you can water with shower water", safety: "Safety rules. Please read.",
    print: "Print the plan", download: "Save the plan", details: "How we calculated this",
    estimateNote: "Estimates for a year of average rain. Drinking and cooking water are not included.",
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
    results: {
      jod: ["Money saved", "JOD a year"], trips: ["Fewer tanker trips", "trips a year"],
      water: ["Water reused", "m³ a year"], pay: ["The system pays for itself in", "months"],
    },
    range: (lo, hi) => `Enter a number from ${lo} to ${hi}. Using the nearest one.`,
    line: (g, mm, r, p) => `${g}: about ${mm} mm of rain a year · ${r} m² roof · ${p} people`,
    detailLines: (v) => [
      `Rain used: ${v.rainUsed} m³ · greywater: ${v.grey} m³`,
      `Your roof can catch up to ${v.potential} m³ a year. ${v.overflow} m³ overflows because the tank is full.`,
      `Months the tank runs dry: ${v.dry} of 12`,
      `CO₂ cut: ${v.co2} kg a year`,
      `We assumed a ${v.tankerVolume} m³ tanker at ${v.tankerPrice} JOD and ${v.litres} litres per person a day for cleaning and toilet flushing. All of these are estimates and unverified.`,
    ],
  },
  ar: {
    brand: "رمادي", brand2: "Ramadi-Cycle", otherLang: "English",
    title: "كم يوفّر بيتك من الماء والمال؟",
    intro: "اكتب بعض المعلومات عن بيتك، وستظهر الأرقام وخطة التنفيذ في الأسفل مباشرة.",
    step1: "معلومات البيت", gov: "أين تسكن؟", budget: "كم تريد أن تصرف؟",
    step2: "ما توفّره كل سنة", step3: "خطة التنفيذ",
    rain: "جمع مياه الأمطار من السطح", grey: "إعادة استخدام مياه الدوش والغسالة",
    materials: "ماذا تشتري", colItem: "البند", colQty: "الكمية", total: "التكلفة الكاملة", jod: "دينار",
    pricesNote: "الأسعار تقديرية. اسأل محلاً قريباً عن السعر.",
    plants: "أشجار يمكن سقيها بمياه الدوش", safety: "قواعد السلامة. اقرأها من فضلك.",
    print: "اطبع الخطة", download: "احفظ الخطة", details: "كيف حسبنا هذه الأرقام",
    estimateNote: "تقديرات لسنة أمطار متوسطة. لا تشمل مياه الشرب والطبخ.",
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
    results: {
      jod: ["المال الموفّر", "دينار بالسنة"], trips: ["رحلات صهريج أقل", "رحلة بالسنة"],
      water: ["مياه يعاد استخدامها", "م³ بالسنة"], pay: ["يسترد النظام تكلفته خلال", "شهر"],
    },
    range: (lo, hi) => `أدخل رقماً من ${lo} إلى ${hi}. نستخدم أقرب رقم مسموح.`,
    line: (g, mm, r, p) => `${g}: حوالي ${mm} ملم مطر بالسنة · سطح ${r} م² · ${p} أشخاص`,
    detailLines: (v) => [
      `مياه أمطار مستخدمة: ${v.rainUsed} م³ · مياه رمادية: ${v.grey} م³`,
      `السطح يجمع حتى ${v.potential} م³ بالسنة. يفيض منها ${v.overflow} م³ لأن الخزان يمتلئ.`,
      `أشهر ينفد فيها الخزان: ${v.dry} من 12`,
      `ثاني أكسيد الكربون الموفّر: ${v.co2} كغ بالسنة`,
      `افترضنا: صهريج ${v.tankerVolume} م³ بسعر ${v.tankerPrice} دينار، و${v.litres} لتراً للشخص يومياً للتنظيف وصناديق الطرد. كل هذه الأرقام تقديرية وغير متحقق منها.`,
    ],
  },
};
