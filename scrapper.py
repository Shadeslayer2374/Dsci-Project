import requests
import csv
import re
import json
from datetime import datetime
import pandas as pd
import os
def clean_text(text):
    if isinstance(text, str):
        text = re.sub(r'<.*?>', '', text)  # Remove HTML tags
        text = re.sub(r'[^\w\s,]', ' ', text)  # Keep commas, remove other special chars
        text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
        return text.lower()
    return text

# Function to extract numeric values from salary and experience
def extract_numeric_values(text):
    if isinstance(text, str):
        # For salary (e.g., "₹5-10 LPA" -> (500000, 1000000))
        salary_match = re.search(r'₹?(\d+\.?\d*)\s*-?\s*(\d+\.?\d*)?\s*(lpa|lakh|lac|cr)', text.lower())
        if salary_match:
            min_val = float(salary_match.group(1))
            max_val = float(salary_match.group(2)) if salary_match.group(2) else min_val
            unit = salary_match.group(3)
            if unit in ['lpa', 'lakh', 'lac']:
                min_val *= 100000
                max_val *= 100000
            elif unit == 'cr':
                min_val *= 10000000
                max_val *= 10000000
            return (min_val, max_val)
        
        # For experience (e.g., "2-5 years" -> (2, 5))
        exp_match = re.search(r'(\d+)\s*-?\s*(\d+)?\s*(years|yrs)', text.lower())
        if exp_match:
            min_exp = float(exp_match.group(1))
            max_exp = float(exp_match.group(2)) if exp_match.group(2) else min_exp
            return (min_exp, max_exp)
    
    return (None, None)

# Function to preprocess job details
def preprocess_job_details(job_details):
    processed_jobs = []
    for job in job_details:
        # Clean all text fields
        for key in job:
            if key != 'Tags and Skills':  # Skip cleaning for tags
                job[key] = clean_text(job[key])
        
        # Extract numeric values for salary and experience
        job['Min Salary'], job['Max Salary'] = extract_numeric_values(job['Salary'])
        job['Min Experience'], job['Max Experience'] = extract_numeric_values(job['Experience'])
        
        # Extract posted date (assuming footer contains this info)
        posted_match = re.search(r'(\d+)\s*(day|week|month)', job['Footer Placeholder Label'])
        if posted_match:
            num = int(posted_match.group(1))
            unit = posted_match.group(2)
            if unit == 'day':
                job['Posted Days Ago'] = num
            elif unit == 'week':
                job['Posted Days Ago'] = num * 7
            elif unit == 'month':
                job['Posted Days Ago'] = num * 30
        else:
            job['Posted Days Ago'] = None
            
        # Handle missing values
        for key in job:
            if job[key] in ('n/a', '', None):
                job[key] = 'Not Specified'
                
        processed_jobs.append(job)
    return processed_jobs

def extract_job_details(data):
    job_details = []
    for job in data['jobDetails']:
        job_id = job.get('jobId', 'N/A')
        title = job.get('title', 'N/A')
        company_name = job.get('companyName', 'N/A')
        footer_label = job.get('footerPlaceholderLabel', 'N/A')
        
        # Extract and fix tags_and_skills
        raw_tags = job.get('tagsAndSkills', [])
        tags_and_skills = []
        
        if isinstance(raw_tags, list):
            # If it's a list of individual characters (e.g., ['j','a','v','a'])
            if raw_tags and all(isinstance(item, str) and len(item) == 1 for item in raw_tags):
                # Join all characters into a single string
                raw_text = ''.join(raw_tags)
                # Split by commas
                if ',' in raw_text:
                    tags_and_skills = [tag.strip() for tag in raw_text.split(',')]
                else:
                    tags_and_skills = [raw_text]
            else:
                # Normal case: list of words/phrases
                for item in raw_tags:
                    if isinstance(item, str):
                        tags_and_skills.append(item.strip())
                    elif isinstance(item, dict) and 'label' in item:
                        tags_and_skills.append(item['label'].strip())
                    elif isinstance(item, dict) and 'title' in item:
                        tags_and_skills.append(item['title'].strip())
        elif isinstance(raw_tags, str):
            # If it's already a string, just split by commas
            tags_and_skills = [tag.strip() for tag in raw_tags.split(',')]
        
        # Clean up skill names, removing extra spaces and empty items
        tags_and_skills = [tag for tag in tags_and_skills if tag]
        tags_and_skills_str = ', '.join(tags_and_skills) if tags_and_skills else 'N/A'
        
        # Rest of the extraction (experience, salary, location, etc.)
        placeholders = job.get('placeholders', [])
        experience = 'N/A'
        salary = 'N/A'
        location = 'N/A'
        
        for placeholder in placeholders:
            if placeholder['type'] == 'experience':
                experience = placeholder['label']
            elif placeholder['type'] == 'salary':
                salary = placeholder['label']
            elif placeholder['type'] == 'location':
                location = placeholder['label']
        
        job_description = job.get('jobDescription', 'N/A')
        
        job_details.append({
            'Job ID': job_id,
            'Job Title': title,
            'Company Name': company_name,
            'Footer Placeholder Label': footer_label,
            'Tags and Skills': tags_and_skills_str,  # Now properly formatted
            'Experience': experience,
            'Salary': salary,
            'Location': location,
            'Job Description': job_description,
            'Scraped Date': datetime.now().strftime('%Y-%m-%d')
        })
    
    return job_details

def scrape_naukri_jobs(user_keyword, pages=5):
    url = "https://www.naukri.com/jobapi/v3/search"
    
    headers = {
        'authority': 'www.naukri.com',
        'accept': 'application/json',
        'accept-language': 'en-US,en;q=0.9',
        'appid': '109',
        'clientid': 'd3skt0p',
        'content-type': 'application/json',
        'cookie': '_t_s=direct; _t_ds=cdb1791699365060-40cdb179-0cdb179; _t_us=654A40C4; test=naukri.com; _t_s=direct; _t_r=1030%2F%2F; persona=default; _t_ds=cdb1791699365060-40cdb179-0cdb179; _abck=370FB7E71860E8432F0D794697C5C6B3~0~YAAQB8AsMQ4X3qiLAQAAvgkNqgpeyiX7uLHxTeXWohrol2EtEzNpPOIaEvv3JD+JdI3rS84j4nYDQKF7p0NIgpwBBGX5xAZ9AKzuTcc2Z40l4LOt7vnnBYFOtrQn0pckHV78IMGvznCh0ZHt8qIAa42FGEqRw6DmU4UUqwu9su3FZ1+6swkLeqDuEkwcZYA47+ELk//zE/uz2NI6DkcPeH3XiP1f/IqLv4csOtbRmjy3+z8VFGYXNtaz8ykorl1YNEthRa60UeBVhZt38BltTpCKZzkf8hMT1ROw18miALTF4c532sWrKLHA5jjrNDrxc7SuzYUmtr4GhPqXtD7SlUblveXo0lLp7PPj19rIQZeea5gGlUtKKD8YY3RNobitL59qU2nkhHELuYFVepx1ES2Ou1z71xM=~-1~||-1||~-1; bm_mi=FB878CE50EF5A9720F1237648310C5CE~YAAQZ0k0Fzq8hZWLAQAAwL26qhW7jpmEnSWtuU+8dq2TRcDJOaVFYUY0qF3S3MKQ9XDq3UO0tZ/OnmlspHISud8bSG56eQONrXPa3pRUU5trZ2UIoVIQrH13zZx//ZcWvpoowZbnqM9NH/Y4C0RCYzSBpjvqM7Jttvti+DZEgBa/fQuBeya0+qWtJq4PkUyWNDMzzzF9lLvBYNHjc3trUoEFvK6/LKmP/VSoLBhS4jggT2NRmzVf0ggbj3IWrC9Pv6Dj+1DeRhk1DItFrUXTpCnxucTUyA4PITGntGvjtZbi8J0tr7DTkZdqycmk/frzDKi26PL+IzCyhg==~1; bm_sv=B3140AAC7590D963EB7E7F19C5153313~YAAQZ0k0Fzu8hZWLAQAAwL26qhWmqot7f4DrMC+us1serQjW03izIns/MDZ4nZzHDxYUnaiF5iDHLhzg6KDat5PFr2hRGJtGR0sGlfucsAp/HAbebS8Busf3Z6VpXzGh6PmK3fasbAq3xJeoeB4LZVUfADa/P7P6glw0n7rWrgMaw9Fk4dZIs6LpojC+azGNJhJ5hcfmvGjiGBVUj23/T8VFP/JhcGtrAOEw0chdzC25P/DVaKD6Xyog3vYiDD55~1; ak_bmsc=2D0EBB2E423AA3278C56D270B2C5C295~000000000000000000000000000000~YAAQHNgsMWdFaJSLAQAArMPTqhVOCEe64z0wWGraX3eTSnlFHLMVjs6oXJh4gLbtKaLY9yeZUMJvYXmHyl7Nw9hDQflD6zF/8JlFDlg+F5EvE/i7QhrhrrP9xTnYp7ioNSEbOWgQxvdKw0SLmr+7g6fMY8HUoeMkX+pVWQAxXN6BpViuWy1O47RbXGBMaFRGwyQIPQaYGGbsdQU806Rwlsv3fOynicHY8ziKUCYFJbdMa3RnE5iZFXHaP7ma8eXQRn/ML2xAhRVRk+3n1yxWRp12gh6R0z2XTIOMwGBSCF2+SJkc92VpRwzuG+TiPFT5Ldm/i2sPNG6kBJ7Uhe63Rie5OoQO2cuFnbPfk1V8PinK+qwoDQfnMyUDIuZT461N5puOk353QtMeu/HPML+wgEr3h9R2NR+7oDWbH04ZiUfZ2sFmbSe8R8Cfply9ILRpMMX2haoIv8BHbKCmnBrVdGF4DCZYxZdeyduZ+YrSnilqWYqKItapXrX/AFQNVtfLE1UG5uxaB4Mi+SDTbwKYyXFe3M0SaHx/ML/WYc7KsjSA9q+/7WtxVflKQdH4TsA=',
        'gid': 'LOCATION,INDUSTRY,EDUCATION,FAREA_ROLE',
        'referer': f'https://www.naukri.com/{user_keyword}-jobs-2?k={user_keyword}',
        'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'systemid': 'Naukri',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    }

    params = {
        'noOfResults': '20',
        'urlType': 'search_by_keyword',
        'searchType': 'adv',
        'keyword': user_keyword,
        'pageNo': '1',
        'sort': 'r',
        'k': user_keyword,
        'seoKey': f'{user_keyword}-jobs-2',
        'src': 'jobsearchDesk',
        'latLong': '',
        'sid': '16993781950467590',
    }

    results = []

    for page in range(1, pages + 1):
        params['pageNo'] = str(page)
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                job_details = extract_job_details(data)
                results.extend(job_details)
            else:
                print(f"API request for page {page} failed with status code: {response.status_code}")
        except Exception as e:
            print(f"Error scraping page {page}: {str(e)}")

    # Preprocess the data
    processed_results = preprocess_job_details(results)
    
    # Create directory if it doesn't exist
    os.makedirs('job_data', exist_ok=True)
    
    # Save to CSV
    output_filename = f"job_data/naukri_jobs_{user_keyword}_{datetime.now().strftime('%Y%m%d')}.csv"
    with open(output_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=processed_results[0].keys())
        writer.writeheader()
        writer.writerows(processed_results)
    
    # Also save to JSON for easier loading later
    json_filename = f"job_data/naukri_jobs_{user_keyword}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(processed_results, f, ensure_ascii=False, indent=2)
    
    print(f"Data has been saved to {output_filename} and {json_filename}")
    return processed_results

if __name__ == "__main__":
    user_keyword = input("Enter the job keyword to search for (e.g., 'developer', 'data scientist'): ")
    pages = int(input("Enter number of pages to scrape: "))
    scrape_naukri_jobs(user_keyword, pages)