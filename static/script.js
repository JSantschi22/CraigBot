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
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
async function sendMessage(userInput, chatWindow) {
    console.log("send fired");
    const response = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userInput })
    });

    console.log("before we make the element");
    const botp = document.createElement('p');
    botp.classList.add('bot-msg');
    chatWindow.appendChild(botp);

    console.log("before we make fullText");
    let fullText = '';
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    console.log("pre loop")
    while (true) {
        const { done, value } = await reader.read();
        console.log("done:", done, "value", value);
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.startsWith('data:'));

        for (const line of lines) {
            console.log(JSON.stringify(line));
            const data = line.slice(6).trim();
            console.log(JSON.stringify(data));
            if (!data || data === '[DONE]') continue;
            try {
                const parsed = JSON.parse(data);
                fullText += parsed.delta;
                botp.innerHTML = marked.parse(fullText);
                chatWindow.scrollTop = chatWindow.scrollHeight;
                await sleep(50);
            } catch (e) {
                // incomplete chunk, skip it
            }
        }
    }
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

const chat = document.querySelector("#input-form");
chat.addEventListener('submit', async (e) => {
    e.preventDefault();
    console.log("submit fired");
    let userInp = document.querySelector("#user-input");
    if (!userInp.value) return;
    let toSend = userInp.value;
    userInp.value = '';
    const chatWindow = document.querySelector("#chat-window");
    chatWindow.insertAdjacentHTML('beforeend', `<p class="user-msg">${toSend}</p>`);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    await sendMessage(toSend, chatWindow);
});