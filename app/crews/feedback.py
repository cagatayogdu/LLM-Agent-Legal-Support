import json
from traceback import format_exc
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from litellm.exceptions import RateLimitError

class Feedback():
    def __init__(self, search_processor, causal_processor, max_iterations):
          self.search_processor = search_processor 
          self.causal_processor = causal_processor
          self.max_iterations = max_iterations
    
    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
        retry=retry_if_exception_type(RateLimitError)
    )
    def _execute_with_retry(self, processor, inputs):
        return processor.kickoff(inputs=inputs)
    
    def process_feedback(self, processed_data, confidence_threshold):   
        feedback_suggestions = ""
        current_iteration = 0
        needs_reanalysis = True
        search_data = "Hata"
        causal_data_dict = {}
        
        original_text = ""
        if isinstance(processed_data, dict) and "analiz_için_hazir_metin" in processed_data:
            original_text = processed_data["analiz_için_hazir_metin"]
        elif isinstance(processed_data, str):
            original_text = processed_data

        if hasattr(self.search_processor, "topic"):
            self.search_processor.topic = original_text
        
        if hasattr(self.causal_processor, "topic"):
            self.causal_processor.topic = original_text

        while current_iteration < self.max_iterations:
            print(f"\n= Analiz Döngüsü: {current_iteration + 1} =")
            
            try:
                search_inputs = {
                    'topic': original_text if original_text else processed_data,
                    'confidence_threshold': confidence_threshold,
                    'feedback': feedback_suggestions 
                }

                search_data = self._execute_with_retry(self.search_processor, search_inputs)

                if hasattr(search_data, "model_dump"):
                    search_data = search_data.model_dump()
                
                causal_data = self._execute_with_retry(
                    self.causal_processor, 
                    {
                        'topic': original_text if original_text else processed_data,
                        'feedback': search_data,
                        'confidence_threshold': confidence_threshold
                    }
                )
                    
                if hasattr(causal_data, "model_dump"):
                    causal_data_dict = causal_data.model_dump()
                else:
                    causal_data_dict = causal_data

                # JSON formatından önemli değerlerin çıkarıldığı kısımdır burasıdır.
                if "raw" in causal_data_dict and isinstance(causal_data_dict["raw"], str):
                    raw_content = causal_data_dict["raw"]

                    if raw_content.startswith("```json"):
                        raw_content = raw_content.replace("```json", "").replace("```", "").strip()
                    
                    try:
                        parsed_data = json.loads(raw_content)
                        for key, value in parsed_data.items():
                            causal_data_dict[key] = value
                    except json.JSONDecodeError as e:
                        print(f"JSON parse hatası: {e}")

                needs_reanalysis = causal_data_dict.get("needs_reanalysis", False)
                 
                if isinstance(needs_reanalysis, str):
                    needs_reanalysis = needs_reanalysis.lower() == "true"
                
                feedback_suggestions = causal_data_dict.get("feedback_suggestions", "")
                
                if not feedback_suggestions and "iyileştirme_önerileri" in causal_data_dict:
                    feedback_suggestions = str(causal_data_dict["iyileştirme_önerileri"])
                
                # Kritik eksikler varsa feedback'e eklenir
                if "kritik_eksikler" in causal_data_dict:
                    kritik_eksikler = causal_data_dict["kritik_eksikler"]
                    if kritik_eksikler:
                        if feedback_suggestions:
                            feedback_suggestions += f" Kritik eksikler: {kritik_eksikler}"
                        else:
                            feedback_suggestions = f"Kritik eksikler: {kritik_eksikler}"
                    
                print(f"\nİterasyon {current_iteration + 1} Sonuçları:")
                print(f"needs_reanalysis: {needs_reanalysis} (tip: {type(needs_reanalysis)})")
                print(f"feedback_suggestions: {feedback_suggestions}")
                
                if not needs_reanalysis:
                    print(f"\n= İterasyon Başarılı! Analiz tamamlandı. =")
                    return search_data
                
                print(f"\n= Yetersiz Tanı Güveni. Feedback ile Yeniden Analiz Başlatılıyor =")
                print(f"İterasyon: {current_iteration + 1}/{self.max_iterations}")
                print(f"Feedback Önerileri: {feedback_suggestions}")
                
            except Exception as crew_error:
                print(f"Crew Error: {str(crew_error)}")
                print(f"Detailed Error: {format_exc()}")

            current_iteration += 1
        
        if needs_reanalysis:
            print("\n= Maksimum İterasyon Sayısına Ulaşıldı. En Son Analiz Sonuçları Döndürülüyor =")
            print(f"Final needs_reanalysis: {needs_reanalysis}")
            print(f"Final iteration: {current_iteration}/{self.max_iterations}")
        
        return search_data