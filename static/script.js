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


//API SECTION
async function sendMessage(userInput) {
    const response = await fetch("/chat", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userInput})
    });

    const data = await response.json();
    return data.reply;
}

async function test() {
    const userInput = prompt("Say what to the chatbot?");
    const reply = await sendMessage(userInput);
    alert(reply);
}