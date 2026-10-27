"""Optional QA: pip install playwright; playwright install chromium.
Run against a local disposable instance, never a production inbox.
For optional axe checks, obtain axe-core separately and pass --axe-source.
"""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser()
parser.add_argument('--base-url',default='http://127.0.0.1:8000')
parser.add_argument('--output',default='browser-results')
parser.add_argument('--axe-source')
parser.add_argument('--admin-email')
parser.add_argument('--submit-test-message',action='store_true')
args=parser.parse_args()
base=args.base_url.rstrip('/')
if not base.startswith(('http://127.0.0.1:','http://localhost:')):
    raise SystemExit('Browser smoke tests are restricted to local disposable instances.')
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
axe=Path(args.axe_source).read_text() if args.axe_source else None
report={'base_url':base,'viewports':[],'browser_errors':[],'accessibility':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
    for width,height in [(1440,1100),(768,1024),(390,844),(320,740)]:
        context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
        page=context.new_page();page.on('pageerror',lambda error:report['browser_errors'].append(str(error)))
        response=page.goto(base,wait_until='networkidle');assert response.status==200
        assert page.get_by_role('heading',name='Aanchal Singh',exact=True).count()==1
        overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
        assert not overflow,f'Horizontal overflow at {width}px'
        if width<=650:
            page.get_by_role('button',name='Menu').click()
            assert page.locator('#navigation').is_visible()
            page.keyboard.press('Escape')
            assert page.get_by_role('button',name='Menu').get_attribute('aria-expanded')=='false'
        page.locator('.workflow details').first.locator('summary').click()
        assert page.locator('.workflow details').first.get_attribute('open') is not None
        page.locator('.workflow details').first.locator('summary').click()
        page.evaluate("document.activeElement.blur(); window.scrollTo({top:0,behavior:'instant'});")
        page.wait_for_timeout(150)
        if width==1440:
            page.screenshot(path=str(out/'homepage-desktop.png'))
            page.screenshot(path=str(out/'homepage-full.png'),full_page=True)
        if width==390:page.screenshot(path=str(out/'homepage-mobile.png'),full_page=True)
        if axe:
            page.evaluate(axe)
            result=page.evaluate("async () => await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})")
            report['accessibility'].append({'page':'home','width':width,'violations':[{'id':x['id'],'impact':x['impact'],'description':x['description'],'nodes':[n['target'] for n in x['nodes']]} for x in result['violations']]})
        for route in ['/projects','/publications','/notes','/contact','/admin/login','/about','/privacy']:
            response=page.goto(base+route,wait_until='networkidle');assert response.status==200,(route,response.status)
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'),(width,route)
            if axe and width in (390,1440) and route in ('/contact','/admin/login'):
                page.evaluate(axe)
                result=page.evaluate("async () => await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})")
                report['accessibility'].append({'page':route,'width':width,'violations':[{'id':x['id'],'impact':x['impact'],'nodes':[n['target'] for n in x['nodes']]} for x in result['violations']]})
        report['viewports'].append({'width':width,'height':height,'routes_ok':8,'horizontal_overflow':False})
        context.close()
    # Essential text and navigation must remain reachable with scripting disabled.
    context=browser.new_context(viewport={'width':390,'height':844},java_script_enabled=False)
    page=context.new_page();page.goto(base)
    assert page.locator('h1').is_visible()
    assert page.locator('#navigation').is_visible()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    report['no_javascript_navigation']=True
    page.screenshot(path=str(out/'homepage-no-javascript.png'))
    context.close()
    context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    page=context.new_page();page.goto(base)
    assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior')=='auto'
    report['reduced_motion']=True
    if args.submit_test_message:
        page.goto(base+'/contact')
        page.get_by_label('Your name').fill('Local QA visitor')
        page.get_by_label('Email address',exact=True).fill('qa@example.com')
        page.get_by_label('Subject',exact=True).fill('LOCAL QA ONLY — contact smoke test')
        page.get_by_label('Message',exact=True).fill('This is a disposable local browser test, not a real enquiry.')
        page.get_by_label('I agree to the privacy notice').check()
        page.get_by_role('button',name='Send message').click()
        page.wait_for_url(base+'/contact')
        assert 'Your message was saved securely' in page.locator('body').inner_text()
        report['csrf_contact_submission']=True
    if args.admin_email:
        password=os.environ.get('BROWSER_ADMIN_PASSWORD')
        if not password:raise SystemExit('Set BROWSER_ADMIN_PASSWORD for the local QA account.')
        page.goto(base+'/admin/login')
        page.get_by_label('Administrator email').fill(args.admin_email)
        page.get_by_label('Password',exact=True).fill(password)
        page.get_by_role('button',name='Sign in securely').click()
        page.wait_for_url(base+'/admin/')
        page.screenshot(path=str(out/'admin-dashboard.png'),full_page=True)
        assert 'Make room for discovery.' in page.locator('body').inner_text()
        if axe:
            page.evaluate(axe)
            result=page.evaluate("async () => await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})")
            report['accessibility'].append({'page':'admin-dashboard','width':1440,'violations':[{'id':x['id'],'impact':x['impact'],'nodes':[n['target'] for n in x['nodes']]} for x in result['violations']]})
        page.goto(base+'/admin/content/projects/new')
        page.get_by_label('Title',exact=True).fill('LOCAL QA ONLY — draft project')
        page.get_by_label('Slug',exact=True).fill('local-qa-only')
        page.get_by_label('Summary',exact=True).fill('A disposable browser fixture, not an academic achievement.')
        page.get_by_role('button',name='Save changes').click()
        page.wait_for_url(base+'/admin/content/projects')
        page.get_by_role('link',name='Preview',exact=True).click()
        assert 'PRIVATE ADMIN PREVIEW' in page.locator('body').inner_text()
        guest=browser.new_context();guest_page=guest.new_page()
        assert guest_page.goto(base+'/projects/local-qa-only').status==404
        guest.close()
        report['admin_login_and_private_draft']=True
        page.goto(base+'/admin/')
        page.get_by_role('button',name='Sign out').click()
        page.wait_for_url(base+'/')
        report['admin_logout']=True
    context.close();browser.close()
report['axe_violations_total']=sum(len(x['violations']) for x in report['accessibility'])
(out/'browser-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
assert not report['browser_errors'],report['browser_errors']
assert report['axe_violations_total']==0,'See browser-report.json for accessibility findings.'
