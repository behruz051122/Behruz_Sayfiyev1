// js/main.js
// Ilovaning kirish nuqtasi. index.html shu faylni <script type="module"> orqali
// yuklaydi. Bu yerda: (1) barcha modullar import qilinadi, (2) navigatsiya
// (handleNav) markazlashtiriladi, (3) sahifa birinchi ochilganda kerakli
// ma'lumotlar yuklanadi.

import { showScreen } from "./navigate.js";
import { initLightbox } from "./components.js";
import { loadBrand, loadUser, checkIsAdmin } from "./user.js";
import * as Courses from "./courses.js";
import * as Tests from "./tests.js";
import { loadReferral } from "./referral.js";
import { loadLeaderboard, initLeaderboardModule } from "./leaderboard.js";
import { loadProfile } from "./profile.js";
import { loadAdminCourses, loadAdminTests, loadAdminAnalytics, loadAdminSimulators, loadAdminDashboardCards, loadAdminBookProducts, loadAdminFaq, loadAdminStudentResults, loadAdminObjections, loadAdminHomeworkSubjects, initAdminModule, initHomeworkAdminModule } from "./admin.js";
import { loadDashboardCards } from "./home.js";
import { loadBookShop } from "./bookshop.js";
import { loadGameSubjects, initGamesModule } from "./games.js";
import { loadFaq } from "./faq.js";
import { loadStudentResults } from "./studentResults.js";
import { loadHomeworkSubjects, initHomeworkModule } from "./homework.js";

function handleNav(target) {
  if (target === "home") {
    showScreen("home");
  } else if (target === "courses") {
    // Kelajakmediklari_bot tahlili asosida — endi "Kurslar" ikki bosqichli
    // oqim: avval fan tanlanadi, keyin shu fan bo'yicha Nazoratli/Mustaqil
    // guruhlangan ro'yxat ko'rinadi (eski tekis ro'yxat endi faqat
    // "Kitoblar (raqamli)" bo'limida ishlatiladi, pastda ko'ring).
    Courses.setListType("course");
    Courses.loadCourseSubjects();
    showScreen("courses-landing");
  } else if (target === "books") {
    // "Kitoblar" bosh sahifa kartasi endi TO'G'RIDAN-TO'G'RI bosma kitoblar
    // do'koniga olib boradi (Kelajak Mediklari botidagi kabi) — talaba
    // avvalgidek bo'sh "raqamli kitoblar" ro'yxatini ko'rib, keyin alohida
    // banner bosib do'konga o'tishi shart emas.
    loadBookShop();
    showScreen("book-shop");
  } else if (target === "digital-books") {
    // Eski, RAQAMLI kitob/kurs ro'yxati (resource_type='book' courses) —
    // hozircha kamdan-kam ishlatiladi, lekin admin xohlasa shu turdagi kurs
    // qo'sha oladi, shuning uchun kirish yo'lini butunlay o'chirmadik —
    // do'kon ekranidagi kichik havola orqali ochiladi.
    Courses.setListType("book");
    document.getElementById("listTitle").textContent = "Kitoblar (raqamli)";
    Courses.loadCourseList();
    showScreen("list");
  } else if (target === "referral") {
    loadReferral();
    showScreen("referral");
  } else if (target === "tests") {
    Tests.resetTestState();
    showScreen("tests");
  } else if (target === "leaderboard") {
    loadLeaderboard();
    showScreen("leaderboard");
  } else if (target === "profile") {
    loadProfile();
    showScreen("profile");
  } else if (target === "back-to-list") {
    showScreen(Courses.getCourseDetailReturnScreen());
  } else if (target === "back-to-course") {
    Courses.openCourseDetail(Courses.getCurrentCourse().id);
  } else if (target === "back-to-paragraph") {
    Courses.openParagraph(Courses.getCurrentParagraph().id);
  } else if (target === "admin") {
    loadAdminCourses();
    loadAdminTests();
    loadAdminAnalytics();
    loadAdminSimulators();
    loadAdminDashboardCards();
    loadAdminBookProducts();
    loadAdminFaq();
    loadAdminStudentResults();
    loadAdminObjections();
    loadAdminHomeworkSubjects();
    showScreen("admin");
  } else if (target === "games") {
    loadGameSubjects();
    showScreen("games");
  } else if (target === "game-battles") {
    showScreen("game-battles");
  } else if (target === "game-quiz") {
    showScreen("game-quiz");
  } else if (target === "game-result") {
    showScreen("game-result");
  } else if (target === "book-shop") {
    loadBookShop();
    showScreen("book-shop");
  } else if (target === "faq") {
    loadFaq();
    showScreen("faq");
  } else if (target === "student-results") {
    loadStudentResults();
    showScreen("student-results");
  } else if (target === "homework") {
    loadHomeworkSubjects();
  }
}

function bindStaticNav() {
  document.querySelectorAll("[data-nav]").forEach(el => {
    el.addEventListener("click", () => handleNav(el.getAttribute("data-nav")));
  });
  // Boshqa modullar (courses.js, tests.js) o'zlari navigatsiya so'raganda
  // shu hodisani yuboradi (navigate.js -> navigateTo()); shu yerda tinglaymiz.
  document.addEventListener("app:navigate", (e) => handleNav(e.detail.target));
}

// Ochilish splash ekranini yashiradi (fade). loadUser() muvaffaqiyatli
// tugagach yoki (tarmoq xatosi bo'lsa ham foydalanuvchi tiqilib qolmasin
// deb) belgilangan maksimal vaqtdan keyin, qaysi biri oldin bo'lsa — shu
// yashirinadi.
let splashHidden = false;
function hideAppSplash() {
  if (splashHidden) return;
  splashHidden = true;
  const splash = document.getElementById("appSplash");
  if (splash) splash.classList.add("hide");
}

function bootstrap() {
  bindStaticNav();
  initLightbox();
  Tests.initTestsModule();
  initLeaderboardModule();
  initAdminModule();
  initGamesModule();
  initHomeworkModule();
  initHomeworkAdminModule();

  loadBrand();
  loadUser().finally(hideAppSplash);
  checkIsAdmin();
  loadDashboardCards();
  showScreen("home");

  // Fallback: tarmoq juda sekin bo'lsa ham splash abadiy osilib qolmasin.
  setTimeout(hideAppSplash, 6000);
}

bootstrap();
