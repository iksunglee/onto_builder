"""Healthcare domain builder."""

from ontobuilder.core.ontology import Ontology
from ontobuilder.domains.base import DomainBuilder


class HealthcareDomainBuilder(DomainBuilder):
    @property
    def name(self) -> str:
        return "healthcare"

    @property
    def description(self) -> str:
        return "Healthcare and medical domain"

    def build_template(self) -> Ontology:
        onto = Ontology("Healthcare", description="Healthcare domain ontology")

        # Core concepts
        onto.add_concept("Person", description="A person in the healthcare system")
        onto.add_concept("Patient", parent="Person", description="A person receiving care")
        onto.add_concept("Provider", parent="Person", description="A healthcare provider")
        onto.add_concept("Doctor", parent="Provider", description="A medical doctor")
        onto.add_concept("Nurse", parent="Provider", description="A nurse")

        onto.add_concept("Condition", description="A medical condition or diagnosis")
        onto.add_concept("Treatment", description="A medical treatment")
        onto.add_concept("Medication", parent="Treatment", description="A prescribed medication")
        onto.add_concept("Procedure", parent="Treatment", description="A medical procedure")

        onto.add_concept("Facility", description="A healthcare facility")
        onto.add_concept("Hospital", parent="Facility", description="A hospital")
        onto.add_concept("Clinic", parent="Facility", description="A clinic")

        onto.add_concept("Appointment", description="A scheduled visit")

        # Properties
        onto.add_property("Person", "name", data_type="string", required=True)
        onto.add_property("Person", "date_of_birth", data_type="date")
        onto.add_property("Patient", "patient_id", data_type="string", required=True)
        onto.add_property("Condition", "name", data_type="string", required=True)
        onto.add_property("Condition", "severity", data_type="string")
        onto.add_property("Medication", "dosage", data_type="string")
        onto.add_property("Appointment", "date", data_type="date", required=True)

        # Relations
        onto.add_relation("diagnosed_with", source="Patient", target="Condition")
        onto.add_relation("treated_by", source="Patient", target="Provider")
        onto.add_relation("prescribed", source="Provider", target="Medication")
        onto.add_relation("treats", source="Treatment", target="Condition")
        onto.add_relation("works_at", source="Provider", target="Facility")
        onto.add_relation("scheduled_at", source="Appointment", target="Facility")

        return onto

    def get_interview_hints(self) -> dict:
        return {
            "domain": "healthcare",
            "description": self.description,
            "key_concepts": ["Patient", "Provider", "Condition", "Treatment", "Facility"],
            "common_relations": ["diagnosed_with", "treated_by", "prescribed"],
        }

    def get_glossary(self) -> dict[str, str]:
        return {
            "EHR": "Electronic Health Record — a digital version of a patient's chart",
            "ICD": "International Classification of Diseases — standard coding for conditions",
            "Diagnosis": "The identification of a disease or condition",
        }
