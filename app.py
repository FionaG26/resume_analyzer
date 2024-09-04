from flask import Flask, render_template, request, jsonify
import re
from spellchecker import SpellChecker
from textblob import TextBlob
import spacy
import docx2txt
import PyPDF2
import os

app = Flask(__name__)

# Initialize NLP model
nlp = spacy.load("en_core_web_sm")

# Function to extract raw text from a resume (PDF, Word, etc.)
def extract_text_from_file(file_path):
    if file_path.endswith('.docx'):
        return docx2txt.process(file_path)
    elif file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload a .docx or .pdf file.")

def extract_text_from_pdf(file_path):
    pdf_text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            pdf_text += page.extract_text() or ""
    return pdf_text

# Resume Parsing Functions
def extract_contact_info(resume_text):
    contact_info = {}
    contact_info['email'] = re.findall(r'\S+@\S+', resume_text)
    contact_info['phone'] = re.findall(r'\b\d{10,15}\b', resume_text)
    contact_info['linkedin'] = re.findall(r'(https?://[^\s]+)', resume_text)
    return contact_info

def extract_sections(resume_text):
    sections = {}
    sections['work_experience'] = re.findall(
        r'(?<=Work Experience)(.*?)(?=Education)', resume_text, re.DOTALL)
    sections['education'] = re.findall(
        r'(?<=Education)(.*?)(?=Skills|Experience|$)',
        resume_text,
        re.DOTALL)
    sections['skills'] = re.findall(
        r'(?<=Skills)(.*?)(?=Experience|Education|$)',
        resume_text,
        re.DOTALL)
    return sections

# Keyword Matcher
def keyword_matcher(resume_text, job_description):
    def preprocess_text(text): return re.sub(r'\W+', ' ', text.lower())
    resume_text_cleaned = preprocess_text(resume_text)
    job_description_cleaned = preprocess_text(job_description)

    resume_keywords = set([token.text.lower() for token in nlp(
        resume_text_cleaned) if not token.is_stop and not token.is_punct])
    job_keywords = set([token.text.lower() for token in nlp(
        job_description_cleaned) if not token.is_stop and not token.is_punct])

    matched_keywords = resume_keywords & job_keywords
    missing_keywords = job_keywords - resume_keywords
    keyword_density = len(matched_keywords) / len(job_keywords) if job_keywords else 0

    return len(matched_keywords), len(missing_keywords), keyword_density

# Experience Evaluator
def experience_evaluator(work_experience_section, job_description):
    experience_titles = re.findall(
        r'\b(?:Manager|Analyst|Engineer|Scientist|Developer|Technician)\b',
        work_experience_section)
    job_titles = re.findall(
        r'\b(?:Manager|Analyst|Engineer|Scientist|Developer|Technician)\b',
        job_description)
    matched_titles = set(experience_titles) & set(job_titles)
    return len(matched_titles), matched_titles

# Skills Assessor
def skills_assessor(resume_skills, job_skills):
    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills
    return len(matched_skills), len(missing_skills)

# Education Verifier
def education_verifier(education_section, required_degree):
    education_degrees = re.findall(
        r'\b(Bachelor|Master|PhD)\b',
        education_section)
    return any(required_degree.lower() in degree.lower()
               for degree in education_degrees)

# Format Analyzer
def format_analyzer(resume_text):
    has_simple_format = all([
        not bool(re.search(r'\t|\n{2,}', resume_text)),  # No tabs or double line breaks
        not bool(re.search(r'<[^>]*>', resume_text))  # No HTML tags
    ])
    return has_simple_format

# Achievements Analyzer
def achievements_analyzer(resume_text):
    achievements = re.findall(
        r'\b(increased|reduced|improved|saved|achieved|grew|generated)\b.*?(\d+%)',
        resume_text,
        re.I)
    return len(achievements)

# Language Checker
spell = SpellChecker()

def language_checker(resume_text):
    words = resume_text.split()
    misspelled = spell.unknown(words)

    # Grammar check using TextBlob
    blob = TextBlob(resume_text)
    grammatical_errors = []
    for sentence in blob.sentences:
        corrected_sentence = sentence.correct()
        if sentence != corrected_sentence:
            grammatical_errors.append((str(sentence), str(corrected_sentence)))

    return list(misspelled), grammatical_errors

# Diversity & Inclusion Assessor
def diversity_inclusion_assessor(resume_text):
    diversity_keywords = [
        "diverse",
        "inclusion",
        "overcame adversity",
        "socio-economic challenges",
        "first-generation",
        "immigration",
        "LGBTQ+",
        "underrepresented",
        "minority",
        "disability"]
    diversity_mentions = [
        word for word in diversity_keywords if word.lower() in resume_text.lower()]

    return len(diversity_mentions)

# Overall Scorer
def overall_scorer(keyword_score, experience_score, skills_score, education_verifier, format_check, achievements, language_errors, diversity_mentions):
    # Convert scores to floats to avoid type errors
    keyword_score = float(keyword_score)
    experience_score = float(experience_score)
    skills_score = float(skills_score)
    education_check = float(education_verifier)
    format_check = float(format_check)
    achievement_score = float(achievements)
    diversity_score = float(diversity_mentions)

    final_score = (0.25 * keyword_score + 0.25 * experience_score +
                   0.2 * skills_score + 0.1 * education_check +
                   0.1 * format_check + 0.05 * achievement_score +
                   0.05 * diversity_score)  # Adjust weights as needed

    return final_score

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    resume_file = request.files['resume']
    job_description = request.form['job_description']

    if resume_file:
        file_path = os.path.join('uploads', resume_file.filename)
        resume_file.save(file_path)
        resume_text = extract_text_from_file(file_path)
        os.remove(file_path)  # Clean up after processing

        sections = extract_sections(resume_text)
        contact_info = extract_contact_info(resume_text)
        
        # Keyword Matching
        keyword_matches, missing_keywords, keyword_density = keyword_matcher(resume_text, job_description)
        
        # Experience Evaluation
        experience_section = sections.get('work_experience', [''])
        experience_section_text = ' '.join(experience_section) if experience_section else ''
        experience_matches, matched_titles = experience_evaluator(experience_section_text, job_description)
        
        # Skills Assessment
        skills_section = sections.get('skills', [''])
        skills_text = ' '.join(skills_section) if skills_section else ''
        job_skills = set(re.findall(r'\b(\w+)\b', job_description))
        resume_skills = set(re.findall(r'\b(\w+)\b', skills_text))
        skills_matches, missing_skills = skills_assessor(resume_skills, job_skills)
        
        # Education Verification
        education_section = sections.get('education', [''])
        education_text = ' '.join(education_section) if education_section else ''
        required_degree = 'Master'  # Example degree requirement
        education_verified = education_verifier(education_text, required_degree)
        
        # Format Analysis
        format_check = format_analyzer(resume_text)
        
        # Achievements Analysis
        achievements_count = achievements_analyzer(resume_text)
        
        # Language Check
        misspelled_words, grammatical_errors = language_checker(resume_text)
        
        # Diversity & Inclusion
        diversity_mentions = diversity_inclusion_assessor(resume_text)
        
        # Final Score
        final_score = overall_scorer(
            keyword_density, experience_matches, skills_matches,
            education_verified, format_check, achievements_count,
            len(misspelled_words), diversity_mentions
        )
        
        results = {
            'keyword_score': keyword_density,
            'experience_score': experience_matches,
            'skills_score': skills_matches,
            'education_check': education_verified * 100,
            'format_check': format_check * 100,
            'achievements': achievements_count,
            'misspelled_words': ', '.join(misspelled_words),
            'grammatical_errors': len(grammatical_errors),
            'diversity_mentions': diversity_mentions,
            'final_score': final_score * 100
        }

        return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)

