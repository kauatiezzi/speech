// Engine.js - VERSÃO FINAL: Foco em velocidade e simplicidade.
(function() {
    'use strict';
    
    const resultSpeaker = document.querySelector('#resultSpeak');
    if (!resultSpeaker) {
        console.error('Elemento #resultSpeak não encontrado.');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        resultSpeaker.textContent = 'error_support';
        return;
    }

    let recognition;
    let silenceTimer;

    function setupRecognition(language) {
        recognition = new SpeechRecognition();
        recognition.lang = language;
        recognition.continuous = true;
        recognition.interimResults = true; // Essencial para a resposta em tempo real
        recognition.maxAlternatives = 1;

        recognition.onresult = function(event) {
            clearTimeout(silenceTimer);
            let transcript = '';
            // Constrói a transcrição completa a partir dos resultados
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                transcript += event.results[i][0].transcript;
            }
            
            // A única tarefa é atualizar o elemento com o que está sendo ouvido.
            resultSpeaker.textContent = transcript.trim();
            
            // Se o resultado for final, agenda uma limpeza do texto para indicar uma nova frase.
            if (event.results[event.results.length - 1].isFinal) {
                silenceTimer = setTimeout(() => {
                    // Limpar o texto aqui sinaliza ao Python que a frase acabou.
                    if (resultSpeaker.textContent === transcript.trim()) {
                         resultSpeaker.textContent = '';
                    }
                }, 750); // Tempo de silêncio para limpar.
            }
        };

        recognition.onend = function() {
            // Reinicia automaticamente se parar
            setTimeout(() => {
                try { 
                    recognition.start(); 
                } catch(e) {
                    // Ignora o erro se já estiver iniciado
                }
            }, 100);
        };

        recognition.onerror = function(event) {
            if (event.error !== 'no-speech') {
                 console.error('Erro de reconhecimento:', event.error);
            }
        };
        
        try {
            recognition.start();
            console.log('Engine de voz iniciada em modo de baixo delay.');
        } catch(e) {
            console.error("Erro ao iniciar a engine:", e);
        }
    }

    // Espera o Python definir o idioma para iniciar
    const languageCheckInterval = setInterval(() => {
        const language = document.getElementById('lg')?.textContent;
        if (language && language !== 'Looking...') {
            clearInterval(languageCheckInterval);
            setupRecognition(language);
        }
    }, 100);

})();