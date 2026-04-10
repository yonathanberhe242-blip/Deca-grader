import streamlit as st
import pdfplumber
import re
import os
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="DECA Test Grader", page_icon="🎯")

class DECATestProcessor:
    def __init__(self):
        self.answer_key = {}
    
    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF (digital text only)"""
        text = ""
        try:
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
        return text
    
    def extract_student_answers(self, text):
        """Extract answers like '1. A' or '1) B'"""
        answers = {}
        patterns = [
            r'(\d{1,3})[\.\)]\s*([A-E])',
            r'(\d{1,3})\s*[\-\—]\s*([A-E])',
            r'Answer[\s#]*(\d{1,3})[\.\)]?\s*[:\-]?\s*([A-E])'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    num = int(match[0])
                    ans = match[1].upper()
                    if 1 <= num <= 100:
                        answers[num] = ans
                except:
                    continue
        return answers
    
    def grade_test(self, student_answers, answer_key):
        """Compare and score"""
        correct = 0
        incorrect = 0
        unanswered = 0
        details = []
        
        for q_num in range(1, 101):
            student_ans = student_answers.get(q_num)
            correct_ans = answer_key.get(q_num, 'N/A')
            
            if student_ans is None:
                status = "unanswered"
                unanswered += 1
            elif student_ans == correct_ans:
                status = "correct"
                correct += 1
            else:
                status = "incorrect"
                incorrect += 1
            
            details.append({
                'question': q_num,
                'student_answer': student_ans if student_ans else "-",
                'correct_answer': correct_ans,
                'status': status
            })
        
        score = (correct / 100) * 100
        return {
            'score': round(score, 2),
            'correct': correct,
            'incorrect': incorrect,
            'unanswered': unanswered,
            'passing': score >= 70,
            'details': details
        }

# Initialize
processor = DECATestProcessor()

st.title("🎯 DECA Test Grader")
st.markdown("Upload PDF files to grade 100-question DECA tests")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Answer Key")
    key_file = st.file_uploader("Upload answer key PDF", type="pdf", key="key")
    
    if key_file:
        with st.spinner("Reading answer key..."):
            text = processor.extract_text_from_pdf(BytesIO(key_file.read()))
            answers = {}
            for line in text.split('\n'):
                match = re.match(r'(\d{1,3})[\.\)]\s*([A-E])', line.strip())
                if match:
                    answers[int(match.group(1))] = match.group(2)
            processor.answer_key = answers
            
            if len(answers) > 0:
                st.success(f"✅ Loaded {len(answers)} answers")
            else:
                st.error("⚠️ No answers found. Format should be: '1. A'")

with col2:
    st.header("2. Student Test")
    test_file = st.file_uploader("Upload student test PDF", type="pdf", key="test")

if test_file and processor.answer_key:
    st.header("3. Results")
    
    with st.spinner("Grading..."):
        text = processor.extract_text_from_pdf(BytesIO(test_file.read()))
        student_answers = processor.extract_student_answers(text)
        results = processor.grade_test(student_answers, processor.answer_key)
    
    # Score display
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", f"{results['score']}%")
    c2.metric("Correct", results['correct'], delta=f"+{results['correct']}")
    c3.metric("Wrong", results['incorrect'], delta=f"-{results['incorrect']}", delta_color="inverse")
    c4.metric("Blank", results['unanswered'])
    
    if results['passing']:
        st.success("🎉 PASSED! (70% or higher)")
    else:
        st.error("📚 Needs Improvement (Below 70%)")
    
    # Detailed breakdown
    st.subheader("Question Breakdown")
    
    # Create tabs for filtering
    tab1, tab2, tab3 = st.tabs(["All Questions", "Wrong Answers", "Unanswered"])
    
    with tab1:
        df = pd.DataFrame(results['details'])
        st.dataframe(df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button("Download CSV Report", csv, "deca_results.csv", "text/csv")
    
    with tab2:
        wrong = [q for q in results['details'] if q['status'] == 'incorrect']
        if wrong:
            for item in wrong:
                st.error(f"❌ **Q{item['question']}**: Student: **{item['student_answer']}** | Correct: **{item['correct_answer']}**")
        else:
            st.balloons()
            st.write("No wrong answers! Perfect score!")
    
    with tab3:
        blank = [q for q in results['details'] if q['status'] == 'unanswered']
        if blank:
            st.warning(f"{len(blank)} questions unanswered")
            st.write([q['question'] for q in blank])
        else:
            st.write("All questions answered!")

    # Summary stats
    st.divider()
    st.caption(f"Graded {len([x for x in results['details'] if x['student_answer'] != '-'])} questions")
