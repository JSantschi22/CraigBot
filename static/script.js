//Get/create the session ID
function generateUUID() {
    if (crypto.randomUUID) {
        return crypto.randomUUID();
    }
    // fallback for non-secure contexts
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
}

let session_id = localStorage.getItem('craigbot_session_id');
if (!session_id) {
    session_id = generateUUID();
    localStorage.setItem('craigbot_session_id', session_id);
}

//info button scripts
/**
 * Shows and hides the info panel with the built-in CSS animations
 */
const toggleInfo = () => {
    const info = document.querySelector("#info");
    if (info.classList.contains('show')) { //if its already being displayed
        info.classList.add('hide'); //play the fadeout animation
        info.addEventListener('animationend', () => {
            info.classList.remove('show', 'hide'); //keep it hidden after the animation ends
        }, {once:true}); //only play the animation once
    } else {
        info.classList.add('show'); //otherwise display it
    }
}

/**
 * Adds the event listeners to show and hide the info panel
 */
document.querySelector("#info-btn").addEventListener('click', toggleInfo);
document.querySelector("#info-close").addEventListener('click', toggleInfo);
document.addEventListener('click', (e) => {
    const info = document.querySelector("#info");
    const infoBtn = document.querySelector("#info-btn")
    if (!info.contains(e.target) && !infoBtn.contains(e.target)) { //if the user clicks outside the info panel
        if (info.classList.contains('show')) { //and the info panel is being displayed
            info.classList.add('hide'); //play the fadeout
            info.addEventListener('animationend', () => {
                info.classList.remove('show', 'hide'); //and hide it
            }, { once: true }); //play the animation only once
        }
    }
});


//API SECTION
/**
 * A shortcut function to wait for a number of ms. For ux effects.
 * @param ms the number of ms to wait for
 * @returns {Promise<unknown>}
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Sends the users message to the backend and requests the bots response. Streams it in token-by-token.
 * @param userInput the message to the bot
 * @param chatWindow the main window for displaying messages
 * @returns {Promise<void>}
 */
async function sendMessage(userInput, chatWindow) {
    const response = await fetch("/chat", { //sends the user's message to the backend
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userInput, session_id: session_id }) //send the message and the ID
    }); //gets back a JSON with the bots reply

    //Create a new p to put the bots response in and add it to the chat window
    const bot_p = document.createElement('p');
    bot_p.classList.add('bot-msg');
    chatWindow.appendChild(bot_p);

    //Create a variable to add the token-by-token response to and a stream reading setup
    let fullText = '';
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    //Loops to read the stream until it sends the [DONE] token
    while (true) {
        const { done, value } = await reader.read(); //pulls the key values out
        if (done) break; //ends the loops once [DONE] is read

        const chunk = decoder.decode(value); //decodes the response to string
        const lines = chunk.split('\n').filter(l => l.startsWith('data:'));

        //loops through each string token
        for (const line of lines) {
            const data = line.slice(6).trim(); //Removes the 'data: ' from the start of each string token
            if (!data || data === '[DONE]') continue; //skip if [DONE] token or if token is empty
            try { //try and parse the JSON object from the response
                const parsed = JSON.parse(data);
                fullText += parsed.delta; //add the delta value (the bots response)
                bot_p.innerHTML = marked.parse(fullText); //replace the p's content with updated text
                chatWindow.scrollTop = chatWindow.scrollHeight; //ensure chat window is always at lowest point
                await sleep(50); //pause between each token for UX effect
            } catch (e) {
                // incomplete chunk, skip it
            }
        }
    }
}

/**
 * Loads the message history into the chat window
 * @returns {Promise<void>}
 */
async function loadHistory() {
    const response = await fetch(`/history?session_id=${session_id}`);
    const data = await response.json();
    console.log(data);
    if (!data.history) return;
    const chatWindow = document.querySelector("#chat-window");
    for (const m of data.history) {
        if (m.role === 'user') {
            chatWindow.insertAdjacentHTML('beforeend', `<p class="user-msg">${m.content}</p>`);
        } else if (m.role === 'assistant') {
            const bot_p = document.createElement('p');
            bot_p.classList.add('bot-msg');
            bot_p.innerHTML = marked.parse(m.content)
            chatWindow.appendChild(bot_p);
        }
    }
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

//CHAT WINDOW LOGIC
/**
 * Makes the chat input section scale with user input
 * @type {Element}
 */
const input = document.querySelector('#user-input');
input.addEventListener('input', () => {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
});

/**
 * Sets the chat user message to send when enter is pressed, but allows for a new line to be created with
 * shift + enter
 * @type {Element}
 */
const textarea = document.querySelector('#user-input');
textarea.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        textarea.form.requestSubmit();
    }
});

/**
 * Sends the users input message to the sendMessage function and creates the message bubble in the chat window.
 * @type {Element}
 */
const chat = document.querySelector("#input-form");
chat.addEventListener('submit', async (e) => {
    e.preventDefault(); //Don't reload the page
    let userInp = document.querySelector("#user-input");
    if (!userInp.value) return; //if the form is empty don't do anything
    let toSend = userInp.value;
    userInp.value = ''; //clear the input the field
    const chatWindow = document.querySelector("#chat-window");
    chatWindow.insertAdjacentHTML('beforeend', `<p class="user-msg">${toSend}</p>`);
    chatWindow.scrollTop = chatWindow.scrollHeight; //scrolls to bottom to show most recent message
    await sendMessage(toSend, chatWindow);
});

/**
 * Loads the message history of the user on page load
 */
document.addEventListener('DOMContentLoaded', loadHistory);