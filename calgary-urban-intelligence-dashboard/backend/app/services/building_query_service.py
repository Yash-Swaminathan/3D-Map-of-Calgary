import json
import re
import logging
from typing import Dict, List, Optional, Any
from flask import current_app
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

logger = logging.getLogger(__name__)

class BuildingQueryService:
    """Service for processing natural language queries using local Flan-T5 model"""
    
    def __init__(self):
        self.model_name = "google/flan-t5-small"
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Flan-T5 model and tokenizer"""
        try:
            logger.info(f"Loading {self.model_name} model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            # Set model to evaluation mode
            self.model.eval()
            
            # Use CPU for this small model (can be changed to GPU if available)
            if torch.cuda.is_available():
                self.model = self.model.cuda()
                logger.info("Model loaded on GPU")
            else:
                logger.info("Model loaded on CPU")
                
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
            self.tokenizer = None
    
    def process_query(self, user_query: str) -> Dict[str, Any]:
        """
        Process natural language query and extract filter criteria
        
        Args:
            user_query: Natural language query from user
            
        Returns:
            Dictionary with filter criteria and metadata
        """
        try:
            # Try LLM processing if model is available
            if self.model and self.tokenizer:
                llm_result = self._query_local_llm(user_query)
                if llm_result and llm_result.get('filters'):
                    return llm_result
            
            # Fallback to rule-based parsing
            return self._fallback_query_parsing(user_query)
            
        except Exception as e:
            logger.error(f"Error processing query '{user_query}': {e}")
            return self._fallback_query_parsing(user_query)
    
    def _query_local_llm(self, user_query: str) -> Optional[Dict[str, Any]]:
        """
        Query local Flan-T5 model for intelligent query processing
        """
        try:
            # Create a simpler, more effective prompt for Flan-T5
            prompt = f"""Extract filter criteria from this building query: "{user_query}"

What type of filter is this?
- height filter: mention minimum or maximum height
- building type: commercial, residential, mixed_use, industrial
- value filter: mention minimum or maximum dollar amount
- zoning filter: mention zoning code like CC-X, RC-G
- location filter: mention area or neighborhood

Answer with the filter type and value:"""
            
            # Tokenize the input with proper attention mask
            inputs = self.tokenizer(
                prompt, 
                return_tensors="pt", 
                max_length=512, 
                truncation=True,
                padding=True
            )
            
            # Move to same device as model
            if torch.cuda.is_available() and next(self.model.parameters()).is_cuda:
                inputs = {k: v.cuda() for k, v in inputs.items()}
            
            # Generate response with better parameters
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_length=100,
                    num_beams=2,
                    temperature=0.3,
                    do_sample=False,  # Use greedy decoding for more consistent results
                    pad_token_id=self.tokenizer.eos_token_id,
                    early_stopping=True
                )
            
            # Decode the response
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            logger.info(f"LLM response for '{user_query}': {response}")
            
            # Parse the response into filters
            return self._parse_llm_response(response, user_query)
            
        except Exception as e:
            logger.error(f"Error querying local LLM: {e}")
            return None
    
    def _parse_llm_response(self, response: str, original_query: str) -> Dict[str, Any]:
        """Parse LLM response and extract meaningful filters"""
        filters = {}
        response_lower = response.lower()
        original_lower = original_query.lower()
        
        # Enhanced zoning detection
        if 'zoning' in response_lower or any(code in original_query.upper() for code in ['CC-X', 'RC-G', 'M-CG', 'C-C1', 'C-O']):
            # Look for zoning codes in original query
            zoning_match = re.search(r'\b([A-Z]{1,3}-[A-Z0-9]{1,3})\b', original_query.upper())
            if zoning_match:
                filters['zoning'] = zoning_match.group(1)
            else:
                # Check for common zoning patterns
                if 'cc-x' in original_lower or 'ccx' in original_lower:
                    filters['zoning'] = 'CC-X'
                elif 'rc-g' in original_lower or 'rcg' in original_lower:
                    filters['zoning'] = 'RC-G'
        
        # Enhanced building type detection
        if 'building type' in response_lower or 'commercial' in response_lower or 'residential' in response_lower:
            if any(word in original_lower for word in ['commercial', 'office', 'retail', 'store', 'shop']):
                filters['building_type'] = 'commercial'
            elif any(word in original_lower for word in ['residential', 'apartment', 'condo', 'house', 'home']):
                filters['building_type'] = 'residential'
            elif any(word in original_lower for word in ['mixed use', 'mixed-use', 'mixed development']):
                filters['building_type'] = 'mixed_use'
            elif any(word in original_lower for word in ['industrial', 'warehouse', 'factory', 'manufacturing']):
                filters['building_type'] = 'industrial'
        
        # Enhanced height detection
        if 'height' in response_lower:
            height_patterns = [
                (r'(?:over|above|more than|greater than|taller than)\s*(\d+)\s*(?:feet|ft)', 'height_min', 'feet'),
                (r'(?:under|below|less than|shorter than)\s*(\d+)\s*(?:feet|ft)', 'height_max', 'feet'),
                (r'(?:over|above|more than|greater than|taller than)\s*(\d+)\s*(?:meters?|m)', 'height_min', 'meters'),
                (r'(?:under|below|less than|shorter than)\s*(\d+)\s*(?:meters?|m)', 'height_max', 'meters'),
                (r'(\d+)\+?\s*(?:feet|ft)', 'height_min', 'feet'),
                (r'(\d+)\+?\s*(?:meters?|m)', 'height_min', 'meters')
            ]
            
            for pattern, filter_type, unit in height_patterns:
                match = re.search(pattern, original_lower)
                if match:
                    try:
                        value = float(match.group(1))
                        # Convert feet to meters if needed
                        if unit == 'feet':
                            value = value * 0.3048
                        filters[filter_type] = value
                        break
                    except ValueError:
                        continue
        
        # Enhanced value detection
        if 'value' in response_lower or 'dollar' in response_lower:
            value_patterns = [
                (r'(?:worth|valued|assessed).*?(?:over|above|more than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_min'),
                (r'(?:worth|valued|assessed).*?(?:under|below|less than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_max'),
                (r'(?:over|above|more than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_min'),
                (r'(?:under|below|less than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_max')
            ]
            
            for pattern, filter_type in value_patterns:
                match = re.search(pattern, original_lower)
                if match:
                    try:
                        value_str = match.group(1).replace(',', '')
                        value = float(value_str)
                        
                        # Handle suffixes
                        if 'k' in match.group(0) or 'thousand' in match.group(0):
                            value *= 1000
                        elif 'million' in match.group(0) or 'm' in match.group(0):
                            value *= 1000000
                        
                        filters[filter_type] = value
                        break
                    except ValueError:
                        continue
        
        # If we found filters, return with high confidence
        if filters:
            return {
                'success': True,
                'filters': filters,
                'query': original_query,
                'method': 'local_llm',
                'confidence': 0.9
            }
        
        # If no filters found, return empty but successful
        return {
            'success': True,
            'filters': {},
            'query': original_query,
            'method': 'local_llm',
            'confidence': 0.3
        }
    
    def _fallback_query_parsing(self, user_query: str) -> Dict[str, Any]:
        """
        Enhanced fallback rule-based query parsing when LLM fails
        """
        filters = {}
        query_lower = user_query.lower()
        
        # Zoning patterns - enhanced for Calgary
        zoning_codes = ['CC-X', 'RC-G', 'M-CG', 'C-C1', 'C-O', 'I-G', 'R-C1', 'R-C2', 'M-C1', 'M-H1', 'DC']
        for code in zoning_codes:
            if code.lower() in query_lower or code.replace('-', '').lower() in query_lower:
                filters['zoning'] = code
                break
        
        # Building type patterns
        if re.search(r'\b(?:commercial|office|retail|store|shop)\b', query_lower):
            filters['building_type'] = 'commercial'
        elif re.search(r'\b(?:residential|apartment|condo|house|home)\b', query_lower):
            filters['building_type'] = 'residential'
        elif re.search(r'\b(?:mixed.use|mixed.development)\b', query_lower):
            filters['building_type'] = 'mixed_use'
        elif re.search(r'\b(?:industrial|warehouse|factory|manufacturing)\b', query_lower):
            filters['building_type'] = 'industrial'
        
        # Height patterns
        height_patterns = [
            (r'(?:taller than|over|above|more than|greater than)\s*(\d+)\s*(?:feet|ft)', 'height_min', 'feet'),
            (r'(?:shorter than|under|below|less than)\s*(\d+)\s*(?:feet|ft)', 'height_max', 'feet'),
            (r'(?:taller than|over|above|more than|greater than)\s*(\d+)\s*(?:meters?|m)', 'height_min', 'meters'),
            (r'(?:shorter than|under|below|less than)\s*(\d+)\s*(?:meters?|m)', 'height_max', 'meters'),
            (r'(\d+)\+?\s*(?:feet|ft)', 'height_min', 'feet'),
            (r'(\d+)\+?\s*(?:meters?|m)', 'height_min', 'meters')
        ]
        
        for pattern, filter_type, unit in height_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    value = float(match.group(1))
                    # Convert feet to meters if needed
                    if unit == 'feet':
                        value = value * 0.3048
                    filters[filter_type] = value
                    break
                except ValueError:
                    continue
        
        # Value patterns
        value_patterns = [
            (r'(?:worth|valued|assessed)\s*(?:over|above|more than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_min'),
            (r'(?:worth|valued|assessed)\s*(?:under|below|less than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_max'),
            (r'(?:over|above|more than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_min'),
            (r'(?:under|below|less than)\s*\$?([\d,]+)(?:k|thousand|million|m)?', 'value_max')
        ]
        
        for pattern, filter_type in value_patterns:
            match = re.search(pattern, query_lower)
            if match:
                try:
                    value_str = match.group(1).replace(',', '')
                    value = float(value_str)
                    
                    # Handle k/thousand/million suffix
                    if 'k' in match.group(0) or 'thousand' in match.group(0):
                        value *= 1000
                    elif 'million' in match.group(0) or 'm' in match.group(0):
                        value *= 1000000
                    
                    filters[filter_type] = value
                    break
                except ValueError:
                    continue
        
        return {
            'success': True,
            'filters': filters,
            'query': user_query,
            'method': 'rule_based',
            'confidence': 0.8 if filters else 0.2
        } 