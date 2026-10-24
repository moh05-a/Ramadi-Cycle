export type Lang = "en" | "ar";

export const months: Record<Lang, string[]> = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  // Levantine names, as used in Jordan
  ar: ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول", "تشرين الأول", "تشرين الثاني", "كانون الأول"],
};

export const units: Record<Lang, Record<"m3" | "m2" | "jod" | "kg" | "yr" | "months", string>> = {
  en: { m3: "m³", m2: "m²", jod: "JOD", kg: "kg", yr: "/yr", months: "months" },
  ar: { m3: "م³", m2: "م²", jod: "دينار", kg: "كغ", yr: "/سنة", months: "شهراً" },
};

/** Western digits in both languages, as on Jordanian bills and price tags. */
export function num(value: number, decimals = 0): string {
  return value.toLocaleString("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export const copy = {
  generate: { en: "Generate blueprint", ar: "أنشئ خطة التنفيذ" },
  // LRI/PDI isolate the Latin run so the brackets stay in order in RTL
  download: { en: "Download plan (.md)", ar: "نزّل الخطة \u2066(.md)\u2069" },
  empty: {
    en: "Set up the household in the sidebar, then press Generate blueprint.",
    ar: "أدخل بيانات المنزل في الشريط الجانبي، ثم اضغط «أنشئ خطة التنفيذ».",
  },
  fallback: {
    en: "Showing the built-in template plan. No local model was available.",
    ar: "تُعرض الخطة الجاهزة. لم يتوفر نموذج محلي.",
  },
  noModel: {
    en: "Ollama is not running. Blueprints use the built-in template.",
    ar: "Ollama غير مشغّل. ستُستخدم الخطة الجاهزة.",
  },
  passed: { en: "Safety checks passed", ar: "اجتازت الخطة فحوص السلامة" },
  of: { en: "of", ar: "من" },
  disclaimer: {
    en: "General guidance only, not an approved plumbing design or legal advice. Hire a licensed plumber and check local rules before building.",
    ar: "هذه إرشادات عامة وليست تصميماً معتمداً للسباكة ولا استشارة قانونية. استعن بسبّاك مرخّص وتحقق من الأنظمة المحلية قبل التنفيذ.",
  },
  greywaterRule: {
    en: "Only sink, shower and laundry water goes into the greywater system. Never toilet or kitchen water.",
    ar: "تدخل نظام المياه الرمادية مياه المغسلة والدوش والغسالة فقط. لا تُدخل مياه المرحاض أو المطبخ أبداً.",
  },
} satisfies Record<string, Record<Lang, string>>;
