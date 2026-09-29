import os, re, tempfile
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from docx import Document
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

load_dotenv()
TOKEN=os.getenv('TELEGRAM_BOT_TOKEN')
if not TOKEN: raise RuntimeError('Missing TELEGRAM_BOT_TOKEN in .env')

CERTS=[
('Meta Front-End Developer Professional Certificate',['html','css','javascript','typescript','react','next.js','frontend'], 'https://www.coursera.org/professional-certificates/meta-front-end-developer'),
('Meta Back-End Developer Professional Certificate',['python','django','flask','node.js','express','api','rest api','backend','sql'], 'https://www.coursera.org/professional-certificates/meta-back-end-developer'),
('IBM Full Stack Software Developer Professional Certificate',['full stack','frontend','backend','html','css','javascript','react','node.js','python','django','git','api'], 'https://www.coursera.org/professional-certificates/ibm-full-stack-cloud-developer'),
('ISTQB Certified Tester Foundation Level (CTFL)',['testing','unit testing','integration testing','end-to-end','jest','playwright','qa','test automation'], 'https://istqb.org/certifications/certified-tester-foundation-level-ctfl-v4-0/')]
SKILLS=['python','java','c','c++','javascript','typescript','html','css','react','next.js','angular','vue','node.js','express','django','flask','fastapi','spring','api','rest api','postgresql','mysql','sql','mongodb','firebase','git','github','docker','aws','azure','machine learning','deep learning','artificial intelligence','ai','data science','pandas','numpy','tensorflow','pytorch','testing','unit testing','integration testing','end-to-end testing','jest','playwright','selenium','qa','linux']
RESP=['software development','web development','frontend','backend','full stack','api','testing','debugging','database','application','development','deployment','maintenance','automation','integration','design']

def norm(s):
    s=s.lower().replace('nextjs','next.js').replace('nodejs','node.js')
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9+#.\-/ ]+',' ',s)).strip()
def has(s,t):
    s=norm(s); t=norm(t)
    if t in ('c','c++'): return bool(re.search(rf'(?<![a-z]){re.escape(t)}(?![a-z])',s))
    return t in s
def matches(s,terms): return [t for t in terms if has(s,t)]

def extract(path):
    ext=Path(path).suffix.lower()
    if ext=='.pdf': return '\n'.join((p.extract_text() or '') for p in PdfReader(path).pages).strip()
    if ext=='.docx': return '\n'.join(p.text for p in Document(path).paragraphs).strip()
    if ext=='.txt': return Path(path).read_text(encoding='utf-8',errors='ignore').strip()
    raise ValueError('Use PDF, DOCX or TXT.')

def profile(jd):
    skills=matches(jd,SKILLS)[:18]; resp=matches(jd,RESP)[:12]
    elig=[x for x in ['b.tech','btech','b.e','bachelor','2027','2026','graduate'] if has(jd,x)]
    return {'text':jd,'skills':skills,'resp':resp,'elig':elig}

def classify_document(text):
    """Classify a document as JD, resume, or unknown using structural signals.
    This is deliberately conservative: ambiguous documents are rejected instead of
    being silently accepted as the wrong input type.
    """
    t=norm(text)

    jd_terms = [
        'job description','job title','position','role','responsibilities',
        'requirements','qualifications','preferred qualifications','what you will do',
        'what we are looking for','skills required','key responsibilities',
        'salary','ctc','location','hiring','recruitment','apply','eligibility',
        'job role','employment type','about the role'
    ]
    resume_terms = [
        'resume','curriculum vitae','education','academic','experience',
        'work experience','professional experience','projects','project experience',
        'certifications','skills','technical skills','internship','internships',
        'cgpa','gpa','linkedin','github','objective','profile','summary',
        'b.tech','btech','b.e','bachelor of technology','achievements'
    ]
    date_patterns = len(re.findall(r'\b(?:19|20)\d{2}\b', t))
    contact_patterns = len(re.findall(r'\b(?:\+?\d[\d\s().-]{7,}|[\w.+-]+@[\w.-]+\.[a-z]{2,})\b', t))

    jd_score = len(matches(t,jd_terms))
    resume_score = len(matches(t,resume_terms))

    # Strong structural evidence for a candidate resume.
    resume_structure = 0
    if has(t,'education'): resume_structure += 2
    if has(t,'projects') or has(t,'project'): resume_structure += 2
    if has(t,'experience') or has(t,'internship'): resume_structure += 2
    if has(t,'certifications') or has(t,'certification'): resume_structure += 1
    if has(t,'linkedin') or has(t,'github') or contact_patterns: resume_structure += 1
    if date_patterns >= 2: resume_structure += 1

    # Strong structural evidence for a job description.
    jd_structure = 0
    if has(t,'responsibilities'): jd_structure += 2
    if has(t,'requirements') or has(t,'qualifications'): jd_structure += 2
    if has(t,'job description') or has(t,'job role') or has(t,'position'): jd_structure += 2
    if has(t,'salary') or has(t,'ctc') or has(t,'location'): jd_structure += 1
    if has(t,'eligibility') or has(t,'recruitment'): jd_structure += 1

    # Explicitly reject obvious cross-submissions.
    if resume_structure >= 4 and jd_structure <= 2:
        return 'resume'
    if jd_structure >= 4 and resume_structure <= 2:
        return 'jd'

    # Strong evidence from section balance.
    if resume_score >= 4 and resume_score > jd_score + 2:
        return 'resume'
    if jd_score >= 4 and jd_score > resume_score + 2:
        return 'jd'

    return 'unknown'

def analyze(resume,p):
    r=norm(resume); skills=p['skills']; resp=p['resp']; elig=p['elig']
    sm=matches(r,skills); rm=matches(r,resp)
    keyword=round(len(sm)/len(skills)*25) if skills else 12
    technical=round(min(25,len(sm)/max(1,min(len(skills),10))*25))
    ph=matches(r,['project','application','system','web','database','api','github','software','developed','implemented'])
    project=round(min(20,len(ph)/8*20))
    responsibility=round(len(rm)/len(resp)*15) if resp else 8
    eligibility=round(sum(has(r,x) for x in elig)/len(elig)*10) if elig else 10
    sections=['education','skills','project','experience','certification','contact']
    readability=min(10,round(sum(has(r,x) for x in sections)/6*10))
    total=max(0,min(100,keyword+technical+project+eligibility+responsibility+readability))
    missing=[x for x in skills if x not in sm]
    s=[]
    s.append(f"Add {', '.join(missing[:3])} to your Skills section only if you genuinely know them." if missing else 'Move the JD\'s most relevant skills higher in your Skills section.')
    s.append('Rewrite one project bullet to clearly show a JD requirement and what you personally built.')
    s.append('Add measurable results to one or two project bullets where you have genuine numbers.')
    certs=[]
    for name,terms,url in sorted(CERTS,key=lambda c:len(matches(p['text'],c[1])),reverse=True):
        hits=len(matches(p['text'],terms))
        if hits and len(certs)<3: certs.append((name,url))
    if not certs: certs=[CERTS[2][:1]+(CERTS[2][2],)]
    return {'score':total,'params':[('Keyword Match',keyword,25),('Technical Skills Match',technical,25),('Projects/Experience Relevance',project,20),('Education/Eligibility',eligibility,10),('Job Responsibility Match',responsibility,15),('ATS Readability',readability,10)],'suggestions':s[:3],'certs':certs,'matched':sm,'missing':missing}

def fmt_full(r):
    p='\n'.join(f'• {n}: {v}/{m}' for n,v,m in r['params'])
    s='\n'.join(f'{i}. {x}' for i,x in enumerate(r['suggestions'],1))
    c='\n'.join(f'{i}. <a href="{u}">{n}</a>' for i,(n,u) in enumerate(r['certs'],1))
    return f'<b>🎯 ATS SCORE: {r["score"]}/100</b>\n\n<b>📊 PARAMETERS</b>\n{p}\n\n<b>💡 EXACTLY 3 SUGGESTIONS</b>\n{s}\n\n<b>🏆 RECOMMENDED CERTIFICATIONS</b>\n{c}'

async def start(update,context):
    context.user_data.clear()
    context.user_data['stage']='collecting'
    context.user_data['jds']=[]
    context.user_data['resumes']=[]
    await update.message.reply_text(
        '🤖 <b>ResumeMatch AI</b>\n\n'
        'Send the <b>Job Description(s)</b> and <b>resume(s)</b> you want to analyze.\n\n'
        'I will automatically identify each document and place it in the correct category.\n\n'
        'When you have finished uploading them, send <b>/analyze</b>.',
        parse_mode='HTML')

async def next_step(update,context):
    await update.message.reply_text(
        'ℹ️ You do not need to use /next.\n\n'
        'Just keep sending your JD(s) and resume(s). I will identify them automatically.\n\n'
        'When finished, send <b>/analyze</b>.', parse_mode='HTML')

async def handle_doc(update,context):
    doc=update.message.document
    name=doc.file_name or 'document'
    ext=Path(name).suffix.lower()
    if ext not in {'.pdf','.docx','.txt'}:
        return await update.message.reply_text('❌ Please use PDF, DOCX or TXT.')
    path=None
    try:
        with tempfile.NamedTemporaryFile(delete=False,suffix=ext) as f: path=f.name
        await (await context.bot.get_file(doc.file_id)).download_to_drive(path)
        text=extract(path)
        if len(text)<100:
            return await update.message.reply_text(
                f'❌ I could not extract enough text from <b>{name}</b>. Please upload a clearer PDF/DOCX/TXT file.',
                parse_mode='HTML')

        doc_type=classify_document(text)
        if doc_type=='jd':
            context.user_data.setdefault('jds',[]).append({'name':name,'text':text})
            n=len(context.user_data['jds'])
            await update.message.reply_text(
                f'✅ <b>Job Description detected</b>\n{name}\n\n'
                f'JDs collected: <b>{n}</b>\n\n'
                'Send another JD or resume, or send <b>/analyze</b> when finished.',
                parse_mode='HTML')
        elif doc_type=='resume':
            context.user_data.setdefault('resumes',[]).append({'name':name,'text':text})
            n=len(context.user_data['resumes'])
            await update.message.reply_text(
                f'✅ <b>Resume detected</b>\n{name}\n\n'
                f'Resumes collected: <b>{n}</b>\n\n'
                'Send another JD or resume, or send <b>/analyze</b> when finished.',
                parse_mode='HTML')
        else:
            await update.message.reply_text(
                f'⚠️ I could not confidently identify <b>{name}</b> as either a Job Description or a Resume.\n\n'
                'Please upload a document with clear JD sections such as <b>Role, Responsibilities, Requirements</b> or resume sections such as <b>Education, Skills, Projects, Experience</b>.\n\n'
                '❌ This file was not saved.', parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f'❌ Error reading {name}: {e}')
    finally:
        if path and os.path.exists(path): os.remove(path)

async def analyze_cmd(update,context):
    jds=context.user_data.get('jds',[])
    resumes=context.user_data.get('resumes',[])
    if not jds:
        return await update.message.reply_text('⚠️ Please send at least one Job Description before analyzing.')
    if not resumes:
        return await update.message.reply_text('⚠️ Please send at least one resume before analyzing.')

    total=len(jds)*len(resumes)
    await update.message.reply_text(
        f'⏳ Analyzing <b>{len(resumes)} resume(s)</b> against <b>{len(jds)} JD(s)</b>...\n'
        f'Total comparisons: <b>{total}</b>', parse_mode='HTML')

    # Cross-product: every resume is analyzed against every JD.
    all_results=[]
    for ri,resume in enumerate(resumes,1):
        results=[]
        for ji,jd in enumerate(jds,1):
            results.append((jd['name'],analyze(resume['text'],profile(jd['text']))))
        all_results.append((resume['name'],results))

    # Compact score matrix first.
    lines=['<b>📊 ATS ANALYSIS RESULTS</b>','',
           f'Resumes: <b>{len(resumes)}</b>', f'Job Descriptions: <b>{len(jds)}</b>',
           f'Total comparisons: <b>{total}</b>','']
    for ri,(rname,results) in enumerate(all_results,1):
        lines.append(f'<b>Resume {ri}: {rname}</b>')
        for ji,(jname,r) in enumerate(results,1):
            lines.append(f'• JD {ji} — {jname}: <b>{r["score"]}/100</b>')
        lines.append('')
    await update.message.reply_text('\n'.join(lines),parse_mode='HTML')

    # Detailed analysis for every resume × JD pair.
    for ri,(rname,results) in enumerate(all_results,1):
        for ji,(jname,r) in enumerate(results,1):
            await update.message.reply_text(
                f'<b>📄 RESUME {ri} × JD {ji}</b>\n'
                f'Resume: <b>{rname}</b>\n'
                f'JD: <b>{jname}</b>\n\n{fmt_full(r)}',
                parse_mode='HTML', disable_web_page_preview=True)

    await update.message.reply_text(
        '✅ <b>Analysis complete.</b>\n\n'
        'Every submitted resume was compared with every submitted JD.\n'
        'Use /start for a new analysis.', parse_mode='HTML')
    context.user_data.clear()

async def text_handler(update,context):
    await update.message.reply_text('Please upload JDs/resume as PDF, DOCX or TXT. Use /start to begin.')

def main():
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('next',next_step)); app.add_handler(CommandHandler('analyze',analyze_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL,handle_doc)); app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,text_handler))
    print(' ResumeMatch - AI (mode is running.........) ')
    app.run_polling()
if __name__=='__main__': main()
