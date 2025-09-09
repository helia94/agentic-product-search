"""Use case selection instruction prompt"""

USE_CASE_SELECTION_PROMPT = """ given the question and the answer, return the selected use case. Just the use case, no other text.
        Question: {question}
        Answer: {answer}"""