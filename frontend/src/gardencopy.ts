// Wording for the garden page. Plant reasons, the summary and care steps come from the API (model or built-in).
import type { Lang } from "@brand";

type GardenCopy = {
  title: string;
  waterLine: (summer: string, month: string) => string;
  area: string; areaHint: string; range: (lo: string, hi: string) => string;
  wishes: string; wishesHint: string; wishesPlaceholder: string;
  aiTitle: string; aiIntro: string; model: string; design: string; cancel: string; builtIn: string;
  working: (m: string) => string; byModel: (m: string) => string; noModels: string; cloudTag: string; cloudNote: string;
  stale: string;
  fits: string; short: (months: string) => string; areaUsed: (used: string, total: string) => string;
  each: (n: string) => string; peak: (l: string) => string; empty: string;
  chartTitle: string; chartLabel: string; supply: string; demand: string; perWeek: string;
  chartNote: string;
  trace: string; attempt: (n: number) => string; outcomes: Record<"passed" | "rejected" | "error", string>;
  passedAll: (n: number) => string;
  care: string; checks: string; checksLabel: string; of: string; checkRules: Record<string, string>;
  rules: string; mature: string;
};

export const GARDEN: Record<Lang, GardenCopy> = {
  en: {
    title: "What your water can grow",
    waterLine: (summer, month) => `In ${month}, the driest month for your garden, your shower, sink and laundry water gives about ${summer} litres a week. That decides what can grow.`,
    area: "Garden size", areaHint: "The ground you can plant, in square metres.", range: (lo, hi) => `Use a number from ${lo} to ${hi}.`,
    wishes: "What do you want from your garden?", wishesHint: "In your own words, English or Arabic.",
    wishesPlaceholder: "Shade by the wall, fruit for the kids, something green all year",
    aiTitle: "Design it with AI",
    aiIntro: "A model running on this laptop reads your wishes and picks plants. Code checks every month's water and the space before you see it.",
    model: "Model", design: "Design my garden", cancel: "Cancel", builtIn: "Show the built-in garden",
    working: (m) => `${m} is designing your garden. This can take a minute or two on a laptop.`,
    byModel: (m) => `Designed by ${m} on this laptop. Every litre was checked by code.`,
    noModels: "No local model is running, so you see the built-in garden. Install Ollama and pull a model to design your own.",
    cloudTag: "cloud", cloudNote: "This is a cloud model: your garden size, wishes and water numbers are sent to OpenRouter.",
    stale: "Your inputs changed, so the AI garden was cleared. Design it again for the new numbers.",
    fits: "Enough water every month", short: (m) => `Short of water in ${m}`,
    areaUsed: (used, total) => `${used} of ${total} m² planted`,
    each: (n) => `× ${n}`, peak: (l) => `up to ${l} L a week in summer`,
    empty: "There isn't enough water in summer for any plant on the list. More people or laundry loads, or a bigger roof, would change that.",
    chartTitle: "Water for the garden, week by week",
    chartLabel: "Litres a week available to the garden and needed by the plants, by month",
    supply: "Water you have", demand: "Water the plants need", perWeek: "L/week",
    chartNote: "Rain does most of the work in winter. The summer months decide how big the garden can be.",
    trace: "How the AI got here", attempt: (n) => `Attempt ${n}`,
    outcomes: { passed: "passed", rejected: "rejected by the checks", error: "model error" },
    passedAll: (n) => `All ${n} checks passed.`,
    care: "Looking after it", checks: "Checks", checksLabel: "garden checks passed", of: "of",
    checkRules: {},
    rules: "Greywater rules", mature: "Water needs are for plants at full size. Young plants need less, so this garden has room to grow into.",
  },
  ar: {
    title: "ماذا يمكن أن تزرع بمياهك",
    waterLine: (summer, month) => `في ${month}، أكثر الأشهر جفافاً لحديقتك، تعطيك مياه الدوش والمغسلة والغسالة نحو ${summer} لتر أسبوعياً. هذا ما يحدد ماذا يمكن أن ينمو.`,
    area: "مساحة الحديقة", areaHint: "الأرض التي يمكنك زراعتها، بالمتر المربع.", range: (lo, hi) => `اكتب رقماً من ${lo} إلى ${hi}.`,
    wishes: "ماذا تريد من حديقتك؟", wishesHint: "بكلماتك، بالعربية أو الإنجليزية.",
    wishesPlaceholder: "ظل عند السور، فواكه للأولاد، شيء أخضر طوال السنة",
    aiTitle: "صمّمها بالذكاء الاصطناعي",
    aiIntro: "نموذج يعمل على هذا الجهاز يقرأ ما تريده ويختار النباتات. يفحص الكود ماء كل شهر والمساحة قبل أن تراها.",
    model: "النموذج", design: "صمّم حديقتي", cancel: "إلغاء", builtIn: "اعرض الحديقة المدمجة",
    working: (m) => `${m} يصمّم حديقتك الآن. قد يستغرق ذلك دقيقة أو دقيقتين على جهاز محمول.`,
    byModel: (m) => `صمّمها ${m} على هذا الجهاز. فحص الكود كل لتر.`,
    noModels: "لا يوجد نموذج محلي يعمل، لذلك ترى الحديقة المدمجة. ثبّت Ollama وحمّل نموذجاً لتصمّم حديقتك.",
    cloudTag: "سحابي", cloudNote: "هذا نموذج سحابي: تُرسَل مساحة حديقتك ورغباتك وأرقام الماء إلى OpenRouter.",
    stale: "تغيّرت مدخلاتك فأُزيلت حديقة الذكاء الاصطناعي. صمّمها من جديد للأرقام الجديدة.",
    fits: "الماء يكفي كل شهر", short: (m) => `الماء لا يكفي في ${m}`,
    areaUsed: (used, total) => `${used} من ${total} م² مزروعة`,
    each: (n) => `× ${n}`, peak: (l) => `حتى ${l} لتر أسبوعياً في الصيف`,
    empty: "لا يكفي الماء في الصيف لأي نبتة في القائمة. عدد أكبر من الأشخاص أو الغسلات، أو سطح أكبر، يغيّر ذلك.",
    chartTitle: "ماء الحديقة أسبوعاً بأسبوع",
    chartLabel: "اللترات المتاحة للحديقة أسبوعياً وما تحتاجه النباتات، حسب الشهر",
    supply: "الماء المتوفر", demand: "ما تحتاجه النباتات", perWeek: "لتر/أسبوع",
    chartNote: "المطر يقوم بمعظم العمل في الشتاء. أشهر الصيف هي التي تحدد حجم الحديقة.",
    trace: "كيف وصل الذكاء الاصطناعي إلى هذه الحديقة", attempt: (n) => `المحاولة ${n}`,
    outcomes: { passed: "نجحت", rejected: "رفضتها الفحوص", error: "خطأ في النموذج" },
    passedAll: (n) => `نجحت الفحوص الـ${n} كلها.`,
    care: "العناية بها", checks: "الفحوص", checksLabel: "فحوص الحديقة الناجحة", of: "من",
    checkRules: {
      "Every plant is on the greywater-safe list": "كل النباتات من قائمة النباتات الآمنة للمياه الرمادية",
      "Plants fit the garden area": "النباتات تتسع لمساحة الحديقة",
      "Enough water in every month": "الماء يكفي في كل شهر",
      "No banned terms in generated text": "لا كلمات محظورة في النص",
      "Fixed warnings and disclaimer attached": "التحذيرات الثابتة والتنبيه مرفقة",
    },
    rules: "قواعد المياه الرمادية", mature: "حاجة النباتات للماء محسوبة لحجمها الكامل. النباتات الصغيرة تحتاج أقل، فهذه الحديقة تتسع لتكبر.",
  },
};
