//Movement Animation to happen
const card = document.querySelector("#grid-row2");
const container = document.querySelector("#grid-row2");
//Items
const title = document.querySelector(".fancy-writing");
const sneaker = document.querySelector("button");


//Moving Animation Event
document.querySelector("#main-container-grid").addEventListener("mousemove", (e) => {
  let xAxis = (window.innerWidth / 2 - e.pageX) / 25
  let yAxis = (window.innerHeight / 2 - e.pageY) / 25
  card.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
  console.log(`rotateY(${xAxis}deg) rotateX(${yAxis}deg)`)
});
//Animate In
container.addEventListener("mouseenter", (e) => {
    console.log(`rotateY(${xAxis}deg) rotateX(${yAxis}deg)`)

  card.style.transition = "none";
  //Popout
  title.style.transform = "translateZ(150px)";
  sneaker.style.transform = "translateZ(200px) rotateZ(-45deg)";
});
//Animate Out
container.addEventListener("mouseleave", (e) => {
    console.log(`rotateY(${xAxis}deg) rotateX(${yAxis}deg)`)

  card.style.transition = "all 0.5s ease";
  card.style.transform = `rotateY(0deg) rotateX(0deg)`;
  //Popback
  title.style.transform = "translateZ(0px)";
  sneaker.style.transform = "translateZ(0px) rotateZ(0deg)";
});
