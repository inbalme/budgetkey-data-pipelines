from datetime import datetime
import dataflows as DF


now = datetime.now()


def process(row):
    claim_date = row.get('claim_date')
    decision = row.get('decision')
    if claim_date:
        if now < claim_date:
            row['decision'] = 'פתוח'
        else:
            row['decision'] = decision or 'סגור'
    else:
        publication_date = row.get('start_date') or row.get('__created_at')
        if not decision and publication_date:
            if (now - publication_date).days < 30:
                row['decision'] = 'חדש'
            else:
                row['decision'] = 'לא ידוע'


def flow(*_):
    return DF.Flow(process)