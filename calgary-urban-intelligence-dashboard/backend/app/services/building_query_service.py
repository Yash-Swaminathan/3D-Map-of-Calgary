"""Parse supported building questions without requiring ML dependencies at startup."""
import json
import logging
import re
from functools import lru_cache
from flask import current_app
from app.utils.validation import validate_filters

logger = logging.getLogger(__name__)
NUMBER = r'(\d[\d,]*(?:\.\d+)?)'
LOW = r'(?:taller than|higher than|at least|over|above|more than|greater than)'
HIGH = r'(?:shorter than|at most|under|below|less than)'

@lru_cache(maxsize=1)
def load_local_model():
    try:
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        tokenizer = AutoTokenizer.from_pretrained('google/flan-t5-small')
        model = AutoModelForSeq2SeqLM.from_pretrained('google/flan-t5-small')
        model.eval()
        return tokenizer, model
    except Exception:
        logger.exception('Local model unavailable; supported rules remain available')
        return None

class BuildingQueryService:
    def process_query(self, user_query):
        if not isinstance(user_query, str) or not user_query.strip() or len(user_query) > 1000:
            raise ValueError('Question must be a nonempty string of at most 1000 characters.')
        filters = self._parse_rules(user_query)
        method = 'rule_based'
        # Known filters are deterministic. Optional model inference handles other wording.
        if not filters and current_app.config.get('ENABLE_LOCAL_LLM', False):
            loaded = load_local_model()
            if loaded:
                tokenizer, model = loaded
                prompt = ('Return only JSON building filters. Allowed keys: height_min, height_max '
                          '(meters), value_min, value_max (CAD), building_type, zoning. '
                          'Do not invent unsupported criteria. Question: ' + user_query)
                try:
                    inputs = tokenizer(prompt, return_tensors='pt', truncation=True, max_length=512)
                    output = model.generate(**inputs, max_new_tokens=100)
                    candidate = json.loads(tokenizer.decode(output[0], skip_special_tokens=True))
                    filters = validate_filters(candidate)
                    method = 'local_llm'
                except Exception:
                    logger.warning('Model did not return valid filters')
        if filters:
            validate_filters(filters)
        return {'success': bool(filters), 'filters': filters, 'query': user_query,
                'method': method, 'confidence': 0.9 if filters else 0,
                'error': None if filters else 'Try a height, building type, assessed value, or zoning filter.'}

    def _parse_rules(self, question):
        text = question.lower()
        filters = {}
        zoning = re.search(r'\b(?:[a-z]{1,3}-[a-z0-9]{1,3}(?:-[a-z0-9]{1,3})?|dc)\b', text)
        if zoning:
            filters['zoning'] = zoning.group().upper()
        for pattern, kind in [(r'\bmixed[ -]use\b', 'mixed use'),
                              (r'\b(commercial|office|retail|store|shop)\b', 'commercial'),
                              (r'\b(residential|apartments?|condos?|houses?|homes?)\b', 'residential'),
                              (r'\b(industrial|warehouse|factory|manufacturing)\b', 'industrial')]:
            if re.search(pattern, text):
                filters['building_type'] = kind
                break
        for operator, suffix in [(LOW, 'min'), (HIGH, 'max')]:
            height = re.search(operator + r'\s*' + NUMBER + r'\s*(feet|ft|meters?|metres?|m)\b', text)
            if height:
                value = float(height.group(1).replace(',', ''))
                filters['height_' + suffix] = value * 0.3048 if height.group(2) in {'feet', 'ft'} else value
            floors = re.search(operator + r'\s*' + NUMBER + r'\s*(?:floors?|storeys?|stories)\b', text)
            if floors:
                filters['floors_' + suffix] = float(floors.group(1).replace(',', ''))
            money = re.search(operator + r'\s*(\$)?' + NUMBER + r'\s*(million|thousand|k|m)?\b', text)
            if money:
                # A numeric height must never also become a monetary filter.
                following = text[money.end():].lstrip()
                is_height = bool(re.match(r'(?:feet|ft|meters?|metres?|floors?|storeys?|stories)\b', following))
                bare_m = money.group(3) == 'm' and not (money.group(1) or re.search(r'\b(worth|value|valued|assessed|properties)\b', text))
                monetary = money.group(1) or money.group(3) or re.search(r'\b(worth|value|valued|assessed)\b', text)
                if monetary and not is_height and not bare_m:
                    multiplier = {'million': 1e6, 'm': 1e6, 'thousand': 1e3, 'k': 1e3}.get(money.group(3), 1)
                    filters['value_' + suffix] = float(money.group(2).replace(',', '')) * multiplier
        return filters
