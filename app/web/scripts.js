document.addEventListener('DOMContentLoaded', function() {
    const analyzeButton = document.getElementById('analyzeButton');
    const clearButton = document.getElementById('clearButton');
    const legalCaseInput = document.getElementById('legalCase');
    const resultDiv = document.getElementById('result');
    const loadingDiv = document.getElementById('loading');
    const securityStatus = document.getElementById('securityStatus');
    
    initializeSecureCommunication();
    
    async function initializeSecureCommunication() {
        try {
            const success = await secureCommunication.initialize();
            
            if (success) {
                securityStatus.innerHTML = '<i>🔒</i> Güvenli iletişim sağlandı';
                securityStatus.classList.remove('insecure');
                securityStatus.classList.add('secure');
                console.log('Secure communication initialized successfully');
            } else {
                securityStatus.innerHTML = '<i>🔓</i> Güvenli iletişim başarısız oldu';
                console.error('Failed to initialize secure communication');
            }
        } catch (error) {
            securityStatus.innerHTML = '<i>🔓</i> Güvenli iletişim başarısız oldu';
            console.error('Error initializing secure communication:', error);
        }
    }

    analyzeButton.addEventListener('click', async function(e) {
        e.preventDefault();
        
        const legalCase = legalCaseInput.value.trim();
        
        if (!legalCase) {
            alert('Lütfen analiz edilecek bir hukuki durum girin.');
            return;
        }

        loadingDiv.style.display = 'block';
        resultDiv.style.display = 'none';
        
        try {
            let response;
            let data;
            
            if (secureCommunication.isInitialized) {
                const encryptedData = await secureCommunication.encryptData({ legal_case: legalCase });
                
                response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        encrypted_data: encryptedData,
                        session_id: secureCommunication.sessionId
                    })
                });
                
                if (!response.ok) {
                    throw new Error('Analiz sırasında bir hata oluştu');
                }
                
                const encryptedResponse = await response.json();
                
                if (encryptedResponse.encrypted_data) {
                    data = await secureCommunication.decryptData(encryptedResponse.encrypted_data);
                    console.log("Decrypted data received:", data);
                } else {
                    throw new Error('Sunucudan şifrelenmiş yanıt alınamadı');
                }
            } else {
                console.warn('Using unencrypted communication');
                securityStatus.innerHTML = '<i>⚠️</i> Şifrelenmemiş iletişim kullanılıyor';
                securityStatus.classList.remove('secure');
                securityStatus.classList.add('insecure');
                
                response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ legal_case: legalCase })
                });

                if (!response.ok) {
                    throw new Error('Analiz sırasında bir hata oluştu');
                }

                data = await response.json();
                console.log("Regular data received:", data);
            }
            
            if (data && data.tasks_output) {
                const conflictAgent = data.tasks_output.find(agent => 
                    agent.agent === "Hukuki Çelişki Tespit ve Entegrasyon Uzmanı"
                );
                
                if (conflictAgent) {
                    console.log("Found conflict agent:", conflictAgent);
                    console.log("Raw output length:", conflictAgent.raw.length);
                    
                    resultDiv.innerHTML = formatAnalysisOutput(conflictAgent.raw);
                    
                    setupSectionNavigation();
                } else {
                    console.warn("Conflict agent not found in response");
                    resultDiv.textContent = "Hukuki Çelişki Tespit ve Entegrasyon Uzmanı çıktısı bulunamadı.";
                }
            } else {
                resultDiv.textContent = JSON.stringify(data, null, 2);
            }
            
            resultDiv.style.display = 'block';
            
        } catch (error) {
            console.error('Error:', error);
            resultDiv.textContent = 'Hata: ' + error.message;
            resultDiv.style.display = 'block';
        } finally {
            loadingDiv.style.display = 'none';
        }
    });
    
    clearButton.addEventListener('click', function(e) {
        e.preventDefault();
        
        legalCaseInput.value = '';
        resultDiv.style.display = 'none';
        resultDiv.innerHTML = '';
        loadingDiv.style.display = 'none';
        legalCaseInput.focus();
    });
    
    function setupSectionNavigation() {
        const navButtons = document.querySelectorAll('.section-nav-button');
        const sections = document.querySelectorAll('.section');
        
        const group1 = ["Detaylı Hukuki Analiz", "Güçlü Yönler", "Zayıf Yönler", "Hukuki Dayanak Analizi"];
        const group2 = ["Pratik Öneriler", "Risk Yönetimi", "Alternatif Çözüm Yolları", "Tutarsızlık Analizi", "Belirsizlik Alanları", "Güven Değerlendirmesi"];
        
        navButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const isGroupedButton = this.classList.contains('grouped-button');
                
                sections.forEach(section => {
                    section.style.display = 'none';
                });
                
                if (isGroupedButton) {
                    const buttonText = this.textContent.trim();
                    let groupToShow = [];
                    
                    if (buttonText.includes("Detaylı Hukuk Analizi")) {
                        groupToShow = group1;
                    } else if (buttonText.includes("Öneriler")) {
                        groupToShow = group2;
                    }
                    
                    sections.forEach(section => {
                        const sectionTitle = section.querySelector('.section-title').textContent.trim();
                        if (groupToShow.includes(sectionTitle)) {
                            section.style.display = 'block';
                        }
                    });
                } else {
                    document.getElementById(targetId).style.display = 'block';
                }
                
                navButtons.forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
            });
        });
        
        if (navButtons.length > 0) {
            navButtons[0].click();
        }
    }
    
    function formatAnalysisOutput(rawText) {
        if (!rawText) return '';
        
        const sections = [];
        const sectionRegex = /### ([^\n]+)(?:\r?\n)([\s\S]*?)(?=### |$)/g;
        let match;
        
        console.log("Raw text length:", rawText.length); 
        
        while ((match = sectionRegex.exec(rawText)) !== null) {
            const title = match[1].trim();
            const content = match[2].trim();
            
            console.log("Found section:", title, "with content length:", content.length); 
            
            if (title) {
                sections.push({
                    id: 'section-' + title.toLowerCase().replace(/\s+/g, '-'),
                    title: title,
                    content: content
                });
            }
        }
        
        let navHtml = `<div class="section-navigation">`;
        
        const group1 = ["Detaylı Hukuki Analiz", "Güçlü Yönler", "Zayıf Yönler", "Hukuki Dayanak Analizi"];
        const group2 = ["Pratik Öneriler", "Risk Yönetimi", "Alternatif Çözüm Yolları", "Tutarsızlık Analizi", "Belirsizlik Alanları", "Güven Değerlendirmesi"];
        
        const findSectionById = (title) => {
            return sections.find(s => s.title === title);
        };
        
        const usedTitles = [...group1, ...group2];
        if (sections.some(s => group1.includes(s.title))) {
            const firstSection = findSectionById(group1[0]) || findSectionById(group1.find(title => sections.some(s => s.title === title)));
            if (firstSection) {
                navHtml += `<button class="section-nav-button grouped-button" data-target="${firstSection.id}">
                    Detaylı Hukuk Analizi
                </button>`;
            }
        }
        
        if (sections.some(s => group2.includes(s.title))) {
            const firstSection = findSectionById(group2[0]) || findSectionById(group2.find(title => sections.some(s => s.title === title)));
            if (firstSection) {
                navHtml += `<button class="section-nav-button grouped-button" data-target="${firstSection.id}">
                    Öneriler
                </button>`;
            }
        }
        
        sections.forEach(section => {
            if (!usedTitles.includes(section.title)) {
                navHtml += `<button class="section-nav-button" data-target="${section.id}">${section.title}</button>`;
            }
        });
        
        navHtml += `</div>`;
        
        let sectionsHtml = '';
        sections.forEach(section => {
            sectionsHtml += `<div id="${section.id}" class="section">
                <h2 class="section-title">${section.title}</h2>
                <div class="section-content">`;
            
            if (section.title === "Hukuki Dayanak Analizi" || 
                section.title === "Güçlü Yönler" || 
                section.title.includes("Hukuki")) {
                
                sectionsHtml += `<div class="paragraph">${formatParagraph(section.content)}</div>`;
            }
            else if (section.content.match(/^\d+\.\s/m)) {
                const lines = section.content.split('\n').filter(l => l.trim());
                const numberedItems = [];
                let currentItem = "";
                
                lines.forEach(line => {
                    if (line.match(/^\d+\.\s/)) {
                        if (currentItem) numberedItems.push(currentItem);
                        currentItem = line;
                    } else {
                        currentItem += " " + line;
                    }
                });
                
                if (currentItem) numberedItems.push(currentItem);
                
                sectionsHtml += `<ol class="content-list">`;
                numberedItems.forEach(item => {
                    const itemContent = item.replace(/^\d+\.\s+/, '');
                    sectionsHtml += `<li class="list-item">${formatParagraph(itemContent)}</li>`;
                });
                sectionsHtml += `</ol>`;
            } else {
                const contentParts = section.content.includes("\n\n") 
                    ? section.content.split(/\n\n+/) 
                    : [section.content];
                
                contentParts.forEach(part => {
                    if (part.trim().startsWith('**') && part.includes(':**')) {
                        const subsectionMatch = part.match(/\*\*(.*?):\*\*([\s\S]*)/);
                        if (subsectionMatch) {
                            const subsectionTitle = subsectionMatch[1];
                            const subsectionContent = subsectionMatch[2].trim();
                            
                            sectionsHtml += `<div class="subsection">
                                <h3 class="subsection-title">${subsectionTitle}:</h3>
                                <div class="subsection-content">${formatParagraph(subsectionContent)}</div>
                            </div>`;
                        } else {
                            sectionsHtml += `<div class="paragraph">${formatParagraph(part)}</div>`;
                        }
                    } 
                    else if (part.includes('\n- ')) {
                        const listItems = part.split(/\n- /).filter(item => item.trim());
                        const listTitle = listItems.shift(); 
                        
                        sectionsHtml += `<div class="list-section">`;
                        if (listTitle) {
                            sectionsHtml += `<div class="list-title">${formatParagraph(listTitle)}</div>`;
                        }
                        
                        sectionsHtml += `<ul class="content-list">`;
                        listItems.forEach(item => {
                            sectionsHtml += `<li class="list-item">${formatParagraph(item.trim())}</li>`;
                        });
                        sectionsHtml += `</ul></div>`;
                    } 
                    else {
                        sectionsHtml += `<div class="paragraph">${formatParagraph(part)}</div>`;
                    }
                });
            }
            
            sectionsHtml += `</div></div>`;
        });
        
        const html = `<div class="legal-analysis">
            ${navHtml}
            ${sectionsHtml}
        </div>`;
        
        return `
        <style>
            .legal-analysis {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                padding: 20px;
            }
            .section-navigation {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 15px;
                margin-bottom: 25px;
                position: sticky;
                top: 0;
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                z-index: 100;
            }
            .section-nav-button {
                padding: 10px 15px;
                background-color: #2c3e50;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-weight: bold;
                color: white;
                transition: all 0.3s ease;
                font-size: 14px;
                text-align: center;
                min-width: 150px;
            }
            .grouped-button {
                padding: 15px;
                line-height: 1.8;
                min-width: 200px;
            }
            .section-nav-button:hover {
                background-color: #1abc9c;
                transform: translateY(-2px);
            }
            .section-nav-button.active {
                background: linear-gradient(135deg, #3498db, #8e44ad);
                color: white;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            }
            .section {
                margin-bottom: 30px;
                background-color: #f9f9f9;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                border-left: 5px solid #3498db;
                display: none; /* Initially hide all sections */
            }
            .section-title {
                color: #2c3e50;
                font-size: 24px;
                margin-top: 0;
                margin-bottom: 20px;
                padding-bottom: 10px;
                border-bottom: 2px solid #3498db;
                display: flex;
                align-items: center;
            }
            .section-title::before {
                content: "⚖️";
                margin-right: 10px;
                font-size: 20px;
            }
            .section-content {
                padding: 0 10px;
                max-width: 100%;
                overflow-wrap: break-word;
                word-break: break-word;
            }
            .subsection {
                margin-bottom: 20px;
                background-color: #fff;
                padding: 15px;
                border-radius: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .subsection-title {
                color: #34495e;
                font-size: 18px;
                margin-bottom: 10px;
                font-weight: bold;
                border-bottom: 1px solid #e1e4e8;
                padding-bottom: 5px;
            }
            .subsection-content {
                padding-left: 15px;
            }
            .paragraph {
                margin-bottom: 15px;
                text-align: justify;
            }
            .list-section {
                margin-bottom: 20px;
                background-color: #fff;
                padding: 15px;
                border-radius: 6px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }
            .list-title {
                font-weight: bold;
                margin-bottom: 10px;
                color: #34495e;
                border-bottom: 1px solid #e1e4e8;
                padding-bottom: 5px;
            }
            .content-list {
                margin-top: 10px;
                margin-bottom: 15px;
                padding-left: 30px;
            }
            .list-item {
                margin-bottom: 10px;
                line-height: 1.5;
            }
            .numbered-item {
                display: flex;
                margin-bottom: 8px;
                line-height: 1.5;
            }
            .item-number {
                font-weight: bold;
                color: #3498db;
                margin-right: 5px;
                min-width: 25px;
            }
            /* Style for legal references */
            .legal-reference {
                font-weight: 500;
                color: #2980b9;
            }
            /* Highlight important legal terms */
            .legal-term {
                font-style: italic;
            }
            strong {
                color: #8e44ad;
                font-weight: bold;
            }
            @media (max-width: 768px) {
                .section-navigation {
                    padding: 10px;
                    justify-content: center;
                }
                .section-nav-button {
                    padding: 8px 12px;
                    font-size: 12px;
                }
                .section {
                    padding: 15px;
                }
                .subsection, .list-section {
                    padding: 10px;
                }
            }
        </style>
        ${html}`;
    }
    
    function formatParagraph(text) {
        if (!text) return '';
        
        let formatted = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
        formatted = formatted.replace(/(Yargıtay\s+)(\d+)(\.\s+[^\.]+Dairesi)/g, 
            '$1<span class="legal-reference">$2$3</span>');
            
        formatted = formatted.replace(/(Madde\s+)(\d+)([^\d]|$)/g, 
            '<span class="legal-term">$1$2</span>$3');
        
        formatted = formatted.replace(/(^|\n)(\d+)\.\s+(.*?)(?=\n\d+\.|$)/gs, function(match, lineStart, number, content) {
            return lineStart + `<div class="numbered-item"><span class="item-number">${number}.</span> ${content.trim()}</div>`;
        });
        
        formatted = formatted.replace(/\n\s{2,}- (.*?)(?=\n|$)/g, '<br><span style="padding-left:15px; display:block; margin-top:5px;">• $1</span>');
        formatted = formatted.replace(/\n- (.*?)(?=\n|$)/g, '<br>• $1');
        
        formatted = formatted.replace(/\r?\n/g, '<br>');
        
        return formatted;
    }
});