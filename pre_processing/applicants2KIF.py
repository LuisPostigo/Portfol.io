import re
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm")

def create_section_patterns():
    """
    Returns a dictionary of patterns for different resume sections.
    """
    section_titles = {
        'Education': ['education', 'academic background', 'academic history', 'studies'],
        'Skills': ['skills', 'technical skills', 'capabilities'],
        'Work Experience': ['work experience', 'professional experience', 'experience', 'job history', 'employment history', 'relevant work experience'],
        'Certifications': ['certifications', 'licenses', 'accreditations', 'certificates'],
        'Projects': ['projects', 'portfolio'],
        'Service': ['service', 'community service', 'volunteer work'],
        'Leadership': ['leadership', 'leadership experience', 'positions of responsibility', 'leadership and activities']
        # Add more sections as needed
    }
    
    section_patterns = {}
    for section, titles in section_titles.items():
        patterns = [[{'LOWER': title.lower()}] for title in titles]
        section_patterns[section] = patterns
    return section_patterns

def clean_text(text):
    """
    Cleans the text by removing excessive blank lines, standardizing bullet points, and trimming whitespace.
    """
    text = re.sub(r'[\-\•\○\▪\*]+', '-', text)  
    text = re.sub(r'\n[\s]*\-', '\n-', text)
    text = re.sub(r'^[\s]*\-', '-', text, flags=re.MULTILINE)
    text = re.sub(r'\s*\n\s*', '\n', text)
    text = re.sub(r'(\n-)+', '\n-', text)
    text = re.sub(r'[•\.\-]*\n', '\n', text)

    clean_lines = []
    for line in text.split('\n'):
        clean_line = line.strip()
        if clean_line:
            clean_lines.append(clean_line)
    return '\n'.join(clean_lines)

def extract_contact_info(text):
    """
    Uses spaCy NLP and regex to extract contact information like names, phones, emails, and links from the text.
    """
    contact_info = {}
    doc = nlp(text)
    
    #############################################################################
    #                                    NAME                                   #
    #############################################################################

    name_match = None
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            name_match = " ".join(ent.text.strip().split()[:2])
            break

    if name_match:
        contact_info['name'] = name_match

    #############################################################################
    #                                    STATE                                  #
    #############################################################################

    state_match = re.search(r'\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b', text)
    state = state_match.group() if state_match else None
    
    if state:
        contact_info['state'] = state

        location_match = re.search(r'(.+),\s*' + state, text)
        if location_match:
            contact_info['location'] = location_match.group(1).strip()

    #############################################################################
    #                                 PHONE NUMBER                              #
    #############################################################################

    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
    if phone_match:
        contact_info['phone'] = phone_match.group()
    
    #############################################################################
    #                                   EMAIL                                   #
    #############################################################################

    email_matches = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
    if email_matches:
        contact_info['email'] = email_matches
    
    #############################################################################
    #                                   LINKS                                   #
    #############################################################################

    url_matches = re.findall(r'\b[A-Za-z0-9.-]+\.(?:com|org|net|edu|gov|io|ai|co|uk|us)(?:/\S*)?\b', text)
    email_domains = {email.split('@')[1] for email in email_matches}
    filtered_urls = [url for url in url_matches if not any(domain in url for domain in email_domains)]
    
    if filtered_urls:
        contact_info['urls'] = filtered_urls

    return contact_info

def extract_sections(text, section_patterns):
    """
    Extracts and organizes text into sections based on predefined patterns.
    """
    lines = text.strip().split('\n')
    
    first_section_index = None
    for i, line in enumerate(lines):
        if any(title[0]['LOWER'] in line.lower() for titles in section_patterns.values() for title in titles):
            first_section_index = i
            break
    
    if first_section_index is not None:
        top_part = '\n'.join(lines[:first_section_index])
        rest_of_resume = '\n'.join(lines[first_section_index:])
    else:
        top_part = text
        rest_of_resume = ""
    
    contact_info = extract_contact_info(top_part)
    
    doc = nlp(rest_of_resume)
    matcher = Matcher(nlp.vocab)
    for section, patterns in section_patterns.items():
        for pattern in patterns:
            matcher.add(section, [pattern])
    
    matches = matcher(doc)
    sections = {}
    current_section = None
    start_index = 0
    
    sections['contact_info'] = contact_info
    
    for match_id, start, end in matches:
        section = nlp.vocab.strings[match_id]
        if current_section:
            section_text = doc[start_index:start].text.strip()
            sections[current_section] = clean_text(section_text)
        current_section = section
        start_index = end
    
    if current_section:
        section_text = doc[start_index:].text.strip()
        sections[current_section] = clean_text(section_text)

    return sections

def convert_to_kif(sections):
    """
    Converts the extracted sections and contact information into Knowledge Interchange Format.
    """
    kif_statements = []

    contact_info = sections.get('contact_info', {})
    if 'name' in contact_info:
        kif_statements.append(f'(name "{contact_info["name"]}")')
    if 'location' in contact_info:
        kif_statements.append(f'(location "{contact_info["location"]}")')
    if 'state' in contact_info:
        kif_statements.append(f'(state "{contact_info["state"]}")')
    if 'phone' in contact_info:
        kif_statements.append(f'(phone "{contact_info["phone"]}")')
    if 'email' in contact_info:
        for email in contact_info['email']:
            kif_statements.append(f'(email "{email}")')
    if 'urls' in contact_info:
        for url in contact_info['urls']:
            kif_statements.append(f'(url "{url}")')

    for section, content in sections.items():
        if section != 'contact_info':
            kif_statements.append(f'({section} "{content}")')

    return '\n'.join(kif_statements)

if __name__ == "__main__":
    resume_text = """
    Audrey Anderson  
    Auburn, AL  I  (344) 555-9999  I  audreyanderson@auburn.edu  I  linkedin.com/aanderson3 
    
    EDUCATION 
    Auburn University, Auburn, AL 
    
                May 20xx 
    Bachelor of Software Engineering 
    
    Mountain Brook High School, Mountain Brook, AL 
    
                May 20xx 
    GPA: 3.6 / 4.0  
    
    RELEVANT EXPERIENCE  
    Information Technology Department, University of Alabama at Birmingham 
                July 20xx 
    Volunteer 
    • Assisted with issues regarding networking (wired, wireless, and dialup) and email problems for 
    UAB users 
    • Communicated with users through email, phone, and face to face to ensure a positive student 
    experience  
    
    Robotics Team, Mountain Brook High School, Mountain Brook, AL        August 20xx – May 20xx 
    Team Member 
    • Researched solutions to a given set of tasks and designed a robot to complete said tasks 
    • Prototyped and built a final mechatronics-based robot to function and score points 
    autonomously in a competitive setting 
    
    Coding Club, Mountain Brook High School, Mountain Brook, AL            August 20xx – May 20xx 
    Coder 
    • Created a text-based adventure game with a graphical interface in Python 
    
    SERVICE  
    Mercedes Marathon, Student Volunteer 
    
        May 20xx, May 20xx 
    Birmingham Zoo, Zoolight Safari and Boo at the Zoo Event Volunteer 
        July 20xx, July 20xx 
    Saint Francis Xavier Youth Group, Fundraising Volunteer 
    
                    October 20xx 
    Habitat for Humanity, Construction Volunteer 
    
        January 20xx 
    
    LEADERSHIP AND ACTIVITIES 
    Auburn Women’s Chorus 
    
                    August 20xx – present 
    Women’s Acapella Ensemble  
    August 20xx– May 20xx  
    Chamber Choir  
    
            October 20xx –  May 20xx  
    Key Club 
    
            August 20xx – May 20xx  
    Future Business Leaders of America  
    
            August 20xx – May 20xx 
    Student Choir  
    
    November 20xx – March 20xx  
    
    HONORS AND AWARDS 
    National Honor Society  
    
            October 20xx – May 20xx  
    Most Outstanding Choir Member 
    
        January 20xx
    """

    section_patterns = create_section_patterns()
    parsed_sections = extract_sections(resume_text, section_patterns)
    for section, content in parsed_sections.items():
        print(f"{section}:\n{content}\n")
