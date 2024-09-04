// results.js

document.addEventListener('DOMContentLoaded', function() {
    // Example data - replace this with dynamic data from your Flask endpoint
    const results = {
        keyword_score: '75%',
        experience_score: '80%',
        skills_score: '70%',
        education_check: '100%',
        format_check: '90%',
        achievements: '5',
        misspelled_words: 'None',
        grammatical_errors: '2',
        diversity_mentions: '3',
        final_score: '82%'
    };

    document.getElementById('keyword_score').textContent = results.keyword_score;
    document.getElementById('experience_score').textContent = results.experience_score;
    document.getElementById('skills_score').textContent = results.skills_score;
    document.getElementById('education_check').textContent = results.education_check;
    document.getElementById('format_check').textContent = results.format_check;
    document.getElementById('achievements').textContent = results.achievements;
    document.getElementById('misspelled_words').textContent = results.misspelled_words;
    document.getElementById('grammatical_errors').textContent = results.grammatical_errors;
    document.getElementById('diversity_mentions').textContent = results.diversity_mentions;
    document.getElementById('final_score').textContent = results.final_score;
});

