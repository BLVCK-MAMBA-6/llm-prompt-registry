import os
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-3.5-flash')

# Gemini 1.5 Flash Pricing (Approximate per 1 Million tokens)
INPUT_COST_PER_M = 0.075
OUTPUT_COST_PER_M = 0.30

TEST_DATASETS = {
    "summarize_article": [
        {"text": "The stock market crashed today due to inflation fears, dropping 500 points."},
        {"text": "Scientists discovered a new species of deep-sea fish that glows in the dark."},
        {"text": "The local basketball team won the championship for the third year in a row."}
    ],
    "welcome_email": [
        {"user_name": "Alice", "company_name": "Acme Corp"},
        {"user_name": "Bob", "company_name": "TechStart"},
        {"user_name": "Charlie", "company_name": "DataFlow"}
    ]
}

def get_required_variables(prompt_template: str):
    return re.findall(r'\{(\w+)\}', prompt_template)

def run_evaluation(prompt_template: str, prompt_name: str = "unknown"):
    required_vars = get_required_variables(prompt_template)
    test_dataset = TEST_DATASETS.get(prompt_name, TEST_DATASETS["summarize_article"])
    
    results = []
    total_score = 0
    total_latency = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    for i, test_case in enumerate(test_dataset):
        missing_vars = [var for var in required_vars if var not in test_case]
        if missing_vars:
            return [{"error": f"Test dataset missing variables: {missing_vars}"}], 0, {}
        
        try:
            formatted_prompt = prompt_template.format(**test_case)
        except KeyError as e:
            return [{"error": f"Prompt missing variable: {e}"}], 0, {}
            
        # 1. Track Latency
        start_time = time.time()
        response = model.generate_content(formatted_prompt)
        end_time = time.time()
        
        generated_text = response.text
        latency = end_time - start_time
        total_latency += latency
        
        # 2. Track Tokens
        try:
            in_tokens = response.usage_metadata.prompt_token_count
            out_tokens = response.usage_metadata.candidates_token_count
            total_input_tokens += in_tokens
            total_output_tokens += out_tokens
        except Exception:
            in_tokens, out_tokens = 0, 0 # Fallback if metadata missing
            
        # 3. Judge
        judge_prompt = f"Grade this output 1-10 for quality and clarity. Reply ONLY with a number.\nOutput: {generated_text}"
        judge_response = model.generate_content(judge_prompt)
        
        try:
            score = int(''.join(filter(str.isdigit, judge_response.text)))
            if score > 10: score = 10
        except ValueError:
            score = 5
            
        total_score += score
        results.append({
            "input": test_case,
            "output": generated_text,
            "score": score
        })
        
    avg_score = total_score / len(results)
    
    # 4. Calculate Cost
    estimated_cost = ((total_input_tokens / 1_000_000) * INPUT_COST_PER_M) + \
                     ((total_output_tokens / 1_000_000) * OUTPUT_COST_PER_M)
                     
    metrics = {
        "total_latency": round(total_latency, 2),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost": round(estimated_cost, 6)
    }
    
    return results, avg_score, metrics