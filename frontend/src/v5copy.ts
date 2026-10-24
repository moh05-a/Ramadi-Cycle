// Wording for the v5 shell: names, navigation, page intros and buttons. Plan text and warnings come from the API.
import type { Lang } from "@brand";

export type Page = "home" | "garden" | "save" | "plan" | "calc";

type Shell = {
  brand: string; brand2: string; darkMode: string; langLabel: string; homeLink: string;
  skip: string; navLabel: string; navMenu: string; nav: Record<Page, string>;
  top: Record<"start" | "planner" | "calc", string>; stepsLabel: string; back: string; goCalc: string;
  stepOf: (n: number, total: number, title: string) => string;
  title: string; intro: string; heroTag: string; heroCta: string; goGarden: string; goSave: string; goPlan: string;
  tabs: Record<"steps" | "buy" | "plants", string>;
  unreachable: string; noTrees: string; toGarden: string;
};

export const SHELL: Record<Lang, Shell> = {
  en: {
    brand: "Suqya", brand2: "سُقيا", darkMode: "Dark mode", langLabel: "العربية", homeLink: "start page",
    skip: "Skip to content", navLabel: "Pages", navMenu: "Menu",
    nav: { home: "Your home", garden: "Your garden", save: "Savings", plan: "Build plan", calc: "How we calculated" },
    top: { start: "Start", planner: "Planner", calc: "How we calculated" }, stepsLabel: "Planner steps",
    back: "Back", goCalc: "See how we calculated", stepOf: (n, total, title) => `Step ${n} of ${total}: ${title}`,
    title: "What can your home's water grow?",
    heroTag: "For homes in Jordan · Works offline", heroCta: "Check my home",
    intro: "Type in a few facts about your home. We work out how much water you can reuse, what it can grow, and what you save.",
    goGarden: "Plan my garden", goSave: "See my savings", goPlan: "See the build plan",
    tabs: { steps: "Build steps", buy: "What to buy", plants: "Trees" },
    unreachable: "The calculator isn't running. Start it with this command, then try again:",
    noTrees: "Tree and plant suggestions come from the AI garden planner, sized to your water.", toGarden: "Plan my garden",
  },
  ar: {
    brand: "سُقيا", brand2: "Suqya", darkMode: "وضع داكن", langLabel: "العربية", homeLink: "الصفحة الأولى",
    skip: "انتقل إلى المحتوى", navLabel: "الصفحات", navMenu: "القائمة",
    nav: { home: "بيتك", garden: "حديقتك", save: "التوفير", plan: "خطة التنفيذ", calc: "كيف حسبنا" },
    top: { start: "البداية", planner: "المخطِّط", calc: "كيف حسبنا" }, stepsLabel: "خطوات المخطِّط",
    back: "رجوع", goCalc: "اعرف كيف حسبنا", stepOf: (n, total, title) => `الخطوة ${n} من ${total}: ${title}`,
    title: "ماذا يمكن أن تزرع بمياه بيتك؟",
    heroTag: "لبيوت الأردن · يعمل دون إنترنت", heroCta: "افحص بيتي",
    intro: "اكتب بعض المعلومات عن بيتك. نحسب كم ماءً يمكنك إعادة استخدامه، وماذا يمكن أن يزرع، وكم توفّر.",
    goGarden: "خطّط حديقتي", goSave: "اعرض التوفير", goPlan: "اعرض خطة التنفيذ",
    tabs: { steps: "خطوات التنفيذ", buy: "ماذا تشتري", plants: "الأشجار" },
    unreachable: "الحاسبة غير مشغّلة. شغّلها بهذا الأمر ثم حاول مجدداً:",
    noTrees: "اقتراحات الأشجار والنباتات تأتي من مخطّط الحديقة بالذكاء الاصطناعي، على قدر مياهك.", toGarden: "خطّط حديقتي",
  },
};

export const PAGES_ORDER: Page[] = ["home", "garden", "save", "plan", "calc"];
