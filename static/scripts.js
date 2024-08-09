document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        const formData = new FormData(form);
        
        fetch('/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            // Display results in percentage
            document.getElementById('keyword-score').textContent = `${(data.keyword_score * 100).toFixed(2)}%`;
            document.getElementById('experience-score').textContent = `${(data.experience_score * 100).toFixed(2)}%`;
            document.getElementById('skills-score').textContent = `${(data.skills_score * 100).toFixed(2)}%`;
            document.getElementById('education-check').textContent = `${data.education_check}%`;
            document.getElementById('format-check').textContent = `${data.format_check}%`;
            document.getElementById('achievements').textContent = data.achievements;
            document.getElementById('misspelled-words').textContent = data.misspelled_words;
            document.getElementById('grammatical-errors').textContent = data.grammatical_errors;
            document.getElementById('diversity-mentions').textContent = data.diversity_mentions;
            document.getElementById('final-score').textContent = `${data.final_score.toFixed(2)}%`;
        })
        .catch(error => console.error('Error:', error));
    });
});

