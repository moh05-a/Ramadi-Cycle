// Wording for the v5 shell: names, navigation, page intros and buttons. Plan text and warnings come from the API.
import type { Lang } from "@brand";

export type Page = "home" | "save" | "plan" | "calc";

type Shell = {
  brand: string; brand2: string; darkMode: string; langLabel: string;
  skip: string; navLabel: string; navMenu: string; nav: Record<Page, string>;
  title: string; intro: string; goSave: string; goPlan: string;
  tabs: Record<"steps" | "buy" | "plants", string>;
  unreachable: string;
};

export const SHELL: Record<Lang, Shell> = {
  en: {
    brand: "Suqya", brand2: "سُقيا", darkMode: "Dark mode", langLabel: "العربية",
    skip: "Skip to content", navLabel: "Pages", navMenu: "Menu",
    nav: { home: "Your home", save: "Savings", plan: "Build plan", calc: "How we calculated" },
    title: "How much water and money can your home save?",
    intro: "Type in a few facts about your home, then press the button at the bottom to see your savings and build plan.",
    goSave: "See my savings", goPlan: "See the build plan",
    tabs: { steps: "Build steps", buy: "What to buy", plants: "Trees" },
    unreachable: "The calculator isn't running. Start it with this command, then try again:",
  },
  ar: {
    brand: "سُقيا", brand2: "Suqya", darkMode: "وضع داكن", langLabel: "العربية",
    skip: "انتقل إلى المحتوى", navLabel: "الصفحات", navMenu: "القائمة",
    nav: { home: "بيتك", save: "التوفير", plan: "خطة التنفيذ", calc: "كيف حسبنا" },
    title: "كم يوفّر بيتك من الماء والمال؟",
    intro: "اكتب بعض المعلومات عن بيتك، ثم اضغط الزر في الأسفل لترى التوفير وخطة التنفيذ.",
    goSave: "اعرض التوفير", goPlan: "اعرض خطة التنفيذ",
    tabs: { steps: "خطوات التنفيذ", buy: "ماذا تشتري", plants: "الأشجار" },
    unreachable: "الحاسبة غير مشغّلة. شغّلها بهذا الأمر ثم حاول مجدداً:",
  },
};

export const PAGES_ORDER: Page[] = ["home", "save", "plan", "calc"];
