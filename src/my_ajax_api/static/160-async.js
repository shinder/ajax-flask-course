// 使用 NodeJS 執行
function myPromise(n = "a") {
  return new Promise((resolve, reject) => {
    const ms = 100 + Math.random() * 500;
    setTimeout(() => {
      resolve({ n, ms });
    }, ms);
  });
}

for (let i = 0; i < 10; i++) {
  console.log(await myPromise("a" + i));
}
