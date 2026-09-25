import os
import re
from typing import Dict
from faker import Faker
from docx import Document
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

class PiiRedactor:
    def __init__(self):
        self.faker = Faker()
        # Ensure consistent faking across runs if needed, or random every time
        Faker.seed(42)
        
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        
        # Mappings to keep consistency
        self.mappings: Dict[str, str] = {}
        
        self.entity_faker_map = {
            "PERSON": self.faker.name,
            "EMAIL_ADDRESS": self.faker.email,
            "PHONE_NUMBER": self.faker.phone_number,
            "ORGANIZATION": self.faker.company,
            "LOCATION": self.faker.address,
            "US_SSN": self.faker.ssn,
            "CREDIT_CARD": self.faker.credit_card_number,
            "DATE_TIME": self.faker.date,
            "IP_ADDRESS": self.faker.ipv4
        }
        
        self.entities = list(self.entity_faker_map.keys())

    def get_fake_value(self, entity_type: str, original_value: str) -> str:
        # If we've seen this exact string before for any entity (or same entity type), reuse the fake value
        key = f"{entity_type}_{original_value.lower()}"
        if key not in self.mappings:
            if entity_type in self.entity_faker_map:
                fake_val = self.entity_faker_map[entity_type]()
                if entity_type == "LOCATION":
                    fake_val = fake_val.replace("\n", ", ")
                self.mappings[key] = fake_val
            else:
                self.mappings[key] = f"[{entity_type}]"
        return self.mappings[key]

    def redact_text(self, text: str) -> str:
        if not text.strip():
            return text
            
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language='en'
        )
        
        # Presidio anonymizer needs exact operators for each entity
        operators = {}
        for entity in self.entities:
            operators[entity] = OperatorConfig(
                "custom",
                {"lambda": lambda x, entity_type=entity: self.get_fake_value(entity_type, x)}
            )
            
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        return anonymized_result.text

    def process_docx(self, input_path: str, output_path: str):
        doc = Document(input_path)
        
        for paragraph in doc.paragraphs:
            if paragraph.text:
                paragraph.text = self.redact_text(paragraph.text)
                
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text:
                        cell.text = self.redact_text(cell.text)
                        
        doc.save(output_path)

if __name__ == "__main__":
    redactor = PiiRedactor()
    input_file = "Red Herring Prospectus.docx"
    output_file = "Red Herring Prospectus_Redacted.docx"
    
    if os.path.exists(input_file):
        print(f"Processing {input_file}...")
        redactor.process_docx(input_file, output_file)
        print(f"Saved redacted file to {output_file}")
        
        # Print some mappings for validation
        print("\nMappings used:")
        for k, v in list(redactor.mappings.items())[:10]:
            print(f"{k} -> {v}")
    else:
        print(f"File {input_file} not found. Please place it in the same directory.")
