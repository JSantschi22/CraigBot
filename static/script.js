//info button scripts
const toggleInfo = () => {
    const info = document.querySelector("#info");
    if (info.classList.contains('show')) {
        info.classList.add('hide');
        info.addEventListener('animationend', () => {
            info.classList.remove('show', 'hide');
        }, {once:true});
    } else {
        info.classList.add('show');
    }
}
document.querySelector("#info-btn").addEventListener('click', toggleInfo);
document.querySelector("#info-close").addEventListener('click', toggleInfo);
document.addEventListener('click', (e) => {
    const info = document.querySelector("#info");
    const infoBtn = document.querySelector("#info-btn")
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

//CHAT WINDOW LOGIC
const input = document.querySelector('#user-input');
input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
});
const textarea = document.querySelector('#user-input');
textarea.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        textarea.form.requestSubmit();
    }
});

const firstMsg = true;
const chat = document.querySelector("#input-form");
chat.addEventListener('submit', async (e) => {
    e.preventDefault();
    let userInp = document.querySelector("#user-input");
    if (!userInp.value)
        return;
    let toSend = userInp.value;
    userInp.value = '';
    const chatWindow = document.querySelector("#chat-window");
    if (firstMsg === true)
        chatWindow.insertAdjacentHTML('beforeend', `<p class="user-msg first-msg">${toSend}</p>`);
    else
        chatWindow.insertAdjacentHTML('beforeend', `<p class="user-msg">${toSend}</p>`);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    const reply = await sendMessage(toSend);
    chatWindow.insertAdjacentHTML('beforeend', `<div class="bot-msg">${marked.parse(reply)}</div>`);
    chatWindow.scrollTop = chatWindow.scrollHeight;
});
