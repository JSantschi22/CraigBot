//info button scripts
const infoBtn = document.querySelector("#info-btn");
infoBtn.addEventListener('click', (e) => {
    const info = document.querySelector("#info");
    if (info.classList.contains('show')) {
        info.classList.add('hide');
        info.addEventListener('animationend', () => {
            info.classList.remove('show', 'hide');
        }, {once:true});
    } else {
        info.classList.add('show');
    }
});
document.addEventListener('click', (e) => {
    const info = document.querySelector("#info");
    if (!info.contains(e.target) && !infoBtn.contains(e.target)) {
        if (info.classList.contains('show')) {
            info.classList.add('hide');
            info.addEventListener('animationend', () => {
                info.classList.remove('show', 'hide');
            }, { once: true });
        }
    }
});