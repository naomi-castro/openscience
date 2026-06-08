

import requests
import pandas as pd

# ————————————————
# Configuración de API Keys y parámetros
# ————————————————
# API keys and parameters
SCOPUS_API_KEY    = ''
CORE_API_KEY      = ''
WOS_API_KEY       = ''
CROSSREF_MAILTO   = 'mary.yein@uv.cl'     # for polite CrossRef requests
UNPAYWALL_EMAIL   = 'mary.yein@uv.cl'     # required by Unpaywall

# Fetch functions for each API

def fetch_from_scopus(doi):
    url = 'https://api.elsevier.com/content/search/scopus'
    headers = {'X-ELS-APIKey': SCOPUS_API_KEY, 'Accept': 'application/json'}
    fields = [
        'dc:title', 'dc:description', 'author', 'prism:publisher', 'prism:coverDate',
        'subject-area', 'prism:issn', 'dc:language', 'dc:type'
    ]
    params = {'query': f'DOI({doi})', 'field': ','.join(fields)}
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return None, f"Scopus error {resp.status_code}"
    entries = resp.json().get('search-results', {}).get('entry', [])
    if not entries:
        return None, None
    e = entries[0]
    subs = [sa.get('$') or sa.get('abbrev') for sa in e.get('subject-areas', {}).get('subject-area', []) if isinstance(sa, dict)]
    subject = '; '.join(subs).strip() if subs else None
    return ({
        'title':        e.get('dc:title'),
        'abstract':     e.get('dc:description'),
        'participants': e.get('author'),
        'publisher':    e.get('prism:publisher'),
        'date_issued':  e.get('prism:coverDate'),
        'subject':      subject,
        'issn':         e.get('prism:issn'),
        'quartile':     'Not available',
        'language':     e.get('dc:language'),
        'doc_type':     e.get('dc:type'),
        'rights':       'Not available',
        'openaccess':   'Not available'
    }, None)


def fetch_from_core(doi):
    url = 'https://api.core.ac.uk/v3/search/works'
    headers = {'Authorization': f'Bearer {CORE_API_KEY}', 'Content-Type': 'application/json'}
    payload = {'q': f'doi:\"{doi}\"', 'limit': 1}
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return None, f"CORE error {resp.status_code}"
    results = resp.json().get('results', [])
    if not results:
        return None, None
    e = results[0]
    raw_topics = e.get('topics', [])
    subject = '; '.join(raw_topics).strip() if raw_topics else None
    rights = 'open' if e.get('is_oa') else 'closed'
    return ({
        'title':        e.get('title'),
        'abstract':     e.get('abstract'),
        'participants': '; '.join([a.get('name') for a in e.get('authors', [])]),
        'publisher':    e.get('publisher'),
        'date_issued':  e.get('publishedDate'),
        'subject':      subject,
        'issn':         e.get('issn'),
        'quartile':     'Not available',
        'language':     e.get('language'),
        'doc_type':     e.get('type'),
        'rights':       rights,
        'openaccess':   'Not available'
    }, None)


def fetch_from_openalex(doi):
    url = f'https://api.openalex.org/works/https://doi.org/{doi}'
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, f"OpenAlex error {resp.status_code}"
    data = resp.json()
    concepts = data.get('concepts', [])
    subject = '; '.join([c.get('display_name') for c in concepts]).strip() if concepts else None
    is_oa = data.get('is_oa')
    rights = 'open' if is_oa else 'closed'
    oa_route = data.get('oa_status') or None
    return ({
        'title':        data.get('title'),
        'abstract':     'Not available',
        'participants': '; '.join([a.get('author', {}).get('display_name') for a in data.get('authorships', [])]),
        'publisher':    data.get('host_venue', {}).get('publisher'),
        'date_issued':  data.get('publication_date'),
        'subject':      subject,
        'issn':         data.get('host_venue', {}).get('issn_l'),
        'quartile':     data.get('host_venue', {}).get('journal_quartile') or 'Not available',
        'language':     None,
        'doc_type':     data.get('type'),
        'rights':       rights,
        'openaccess':   oa_route
    }, None)


def fetch_from_crossref(doi):
    url = f'https://api.crossref.org/works/{doi}'
    params = {'mailto': CROSSREF_MAILTO}
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return None, f"CrossRef error {resp.status_code}"
    msg = resp.json().get('message', {})
    cr_subjects = msg.get('subject') or []
    subject = '; '.join(cr_subjects).strip() if cr_subjects else None
    rights = 'open' if msg.get('license') else 'closed'
    return ({
        'title':        msg.get('title')[0] if msg.get('title') else None,
        'abstract':     None,
        'participants': None,
        'publisher':    msg.get('publisher'),
        'date_issued':  msg.get('issued', {}).get('date-parts', [[None]])[0][0],
        'subject':      subject,
        'issn':         msg.get('ISSN')[0] if msg.get('ISSN') else None,
        'quartile':     None,
        'language':     msg.get('language'),
        'doc_type':     msg.get('type'),
        'rights':       rights,
        'openaccess':   None
    }, None)


def fetch_from_unpaywall(doi):
    url = f'https://api.unpaywall.org/v2/{doi}?email={UNPAYWALL_EMAIL}'
    resp = requests.get(url)
    if resp.status_code != 200:
        return None, f"Unpaywall error {resp.status_code}"
    data = resp.json()
    is_oa = data.get('is_oa')
    rights = 'open' if is_oa else 'closed'
    oa_route = data.get('oa_status') or None
    return ({
        'title':        None,
        'abstract':     None,
        'participants': None,
        'publisher':    None,
        'date_issued':  None,
        'subject':      None,
        'issn':         None,
        'quartile':     None,
        'language':     None,
        'doc_type':     None,
        'rights':       rights,
        'openaccess':   oa_route
    }, None)


def fetch_from_wos_by_id(wos_id):
    headers = {'X-ApiKey': WOS_API_KEY, 'Accept': 'application/json'}
    url = f'https://api.clarivate.com/apis/wos-starter/v1/documents/{wos_id}'
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return None, f"WOS error {resp.status_code}"
    doc = resp.json()
    if not doc:
        return None, "No document returned"
    raw_kw = doc.get('author_keywords', [])
    subject = '; '.join(raw_kw).strip() if raw_kw else None
    return ({
        'title':        doc.get('title'),
        'abstract':     doc.get('abstractText'),
        'participants': '; '.join(doc.get('authors', [])) if doc.get('authors') else None,
        'publisher':    doc.get('source'),
        'date_issued':  doc.get('publication_date'),
        'subject':      subject,
        'issn':         doc.get('issn'),
        'quartile':     'Not available',
        'language':     doc.get('language'),
        'doc_type':     doc.get('document_type'),
        'rights':       'Not available',
        'openaccess':   'Not available'
    }, None)


def merged_metadata(doi):
    sources = [
        ('Scopus', fetch_from_scopus),
        ('CORE', fetch_from_core),
        ('OpenAlex', fetch_from_openalex),
        ('CrossRef', fetch_from_crossref),
        ('Unpaywall', fetch_from_unpaywall)
    ]
    fields = ['title','abstract','participants','publisher','date_issued',
              'subject','issn','quartile','language','doc_type',
              'rights','openaccess']
    merged = dict.fromkeys(fields, None)
    errors = {f'ERROR_{name}': '' for name, _ in sources}

    for name, fetch in sources:
        result, err = fetch(doi)
        if err:
            errors[f'ERROR_{name}'] = err
        if result:
            for k, v in result.items():
                if merged[k] is None and v not in (None, ''):
                    merged[k] = v
    for k in merged:
        if merged[k] is None:
            merged[k] = 'Not available'
    return merged, errors


def process_doi_excel(input_file):
    df = pd.read_excel(input_file)
    if 'DOI' not in df.columns or 'WOS_ID' not in df.columns:
        raise ValueError("El archivo debe tener columnas 'DOI' y 'WOS_ID'.")

    output_rows = []

    for _, row in df.iterrows():
        doi = row['DOI']
        wos_id = row['WOS_ID']
        base_data = {'DOI': doi, 'WOS_ID': wos_id}

        if pd.notna(wos_id) and str(wos_id).strip() != '':
            print(f"Consultando por WOS_ID: {wos_id}")
            md, err = fetch_from_wos_by_id(wos_id)
            if md:
                base_data.update(md)
            base_data['ERROR_WOS'] = err or ''
        else:
            print(f"Consultando por DOI: {doi}")
            md, errs = merged_metadata(doi)
            base_data.update(md)
            base_data.update(errs)

        output_rows.append(base_data)

    out_df = pd.DataFrame(output_rows)
    out_df.to_excel('hardvested_dois.xlsx', index=False)

# Ejecutar
process_doi_excel('data.xlsx')
