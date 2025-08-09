const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const lectureForm = document.getElementById('lectureForm');
const transcriptArea = document.getElementById('transcript');
const saveForm = document.getElementById('saveLectureForm');

let recognition;
let transcript = '';

startBtn.addEventListener('click', () => {
    if (!('webkitSpeechRecognition' in window)) {
        alert('Speech recognition not supported in your browser');
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    recognition.onstart = () => {
        startBtn.disabled = true;
        stopBtn.disabled = false;
        transcript = '';
    };

    recognition.onresult = (event) => {
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                transcript += event.results[i][0].transcript + ' ';
            } else {
                interimTranscript += event.results[i][0].transcript;
            }
        }
        
        transcriptArea.value = transcript + interimTranscript;
    };

    recognition.onerror = (event) => {
        console.error('Recognition error:', event.error);
    };

    recognition.start();
});

stopBtn.addEventListener('click', () => {
    if (recognition) {
        recognition.stop();
        startBtn.disabled = false;
        stopBtn.disabled = true;
        lectureForm.style.display = 'block';
    }
});

saveForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const formData = {
        title: saveForm.title.value,
        course: saveForm.course.value,
        year: saveForm.year.value,
        content: transcript
    };

    fetch('/save_lecture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'Lecture saved successfully') {
            alert('Lecture saved!');
            window.location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});