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
import { loadLeaderboard } from "./leaderboard.js";
import { loadProfile } from "./profile.js";
import { loadAdminCourses, loadAdminTests, initAdminModule } from "./admin.js";

function handleNav(target) {
  if (target === "home") {
    showScreen("home");
  } else if (target === "courses") {
    Courses.setListType("course");
    document.getElementById("listTitle").textContent = "Kurslar";
    Courses.loadCourseList();
    showScreen("list");
  } else if (target === "books") {
    Courses.setListType("book");
    document.getElementById("listTitle").textContent = "Kitoblar";
    Courses.loadCourseList();
    showScreen("list");
  } else if (target === "referral") {
    loadReferral();
    showScreen("referral");
  } else if (target === "tests") {
    Tests.resetTestState();
    Tests.loadTestList();
    showScreen("tests");
  } else if (target === "leaderboard") {
    loadLeaderboard();
    showScreen("leaderboard");
  } else if (target === "profile") {
    loadProfile();
    showScreen("profile");
  } else if (target === "back-to-list") {
    showScreen("list");
  } else if (target === "back-to-course") {
    Courses.openCourseDetail(Courses.getCurrentCourse().id);
  } else if (target === "back-to-paragraph") {
    Courses.openParagraph(Courses.getCurrentParagraph().id);
  } else if (target === "admin") {
    loadAdminCourses();
    loadAdminTests();
    showScreen("admin");
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

function bootstrap() {
  bindStaticNav();
  initLightbox();
  Tests.initTestsModule();
  initAdminModule();

  loadBrand();
  loadUser();
  checkIsAdmin();
  showScreen("home");
}

bootstrap();
