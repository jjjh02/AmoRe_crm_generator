/**
 * CRM Studio - Toss Style V2
 * Loads brand images from brand_images.json
 */

// Brand data - loaded from JSON
let BRAND_IMAGES = {};

const PERSONA_INFO = {
    'Luxury_Lover': { label: '프리미엄', color: '#9065B0', bg: '#F4F0F7' },
    'Sensitive_Skin': { label: '민감성', color: '#0F7B6C', bg: '#E6FCF5' },
    'Budget_Seeker': { label: '가성비', color: '#D9730D', bg: '#FFF4E6' },
    'Trend_Follower': { label: '트렌드', color: '#E03E8E', bg: '#FFF0F6' },
    'Natural_Beauty': { label: '자연주의', color: '#2383E2', bg: '#E7F5FF' }
};

let BRANDS_DATA = {}, PRODUCTS = [], PERSONAS = [], CAMPAIGN_EVENTS = {};

let state = {
    currentStep: 1, selectedBrand: null, selectedProduct: null,
    stageIndex: null, styleIndex: null, selectedEvent: null, mode: 'simple',
    customData: { brandName: '', brandStory: '', productName: '', productPrice: 0 },
    customPersonas: [], customEvents: [], customStages: [], customStyles: [],
    qwenModel: 'Qwen/Qwen2.5-1.5B-Instruct',
    exaModel: 'LGAI-EXAONE/EXAONE-4.0-1.2B'
};

let AARRR = ['Acquisition', 'Activation', 'Retention', 'Revenue', 'Referral'];
let AARRR_KR = ['유입', '구매', '재구매', '매출', '추천'];
let STYLES_KR = ['긴박', '정보', 'FOMO', '감성', '시즌'];

const API_BASE = window.API_BASE || (location.origin && location.origin !== "null" ? location.origin : "");
const API_ENDPOINT = API_BASE ? `${API_BASE.replace(/\/$/, "")}/generate_batch` : "";

const $ = id => document.getElementById(id);

function getEditableText(el) {
    return (el?.innerText || '').replace(/\u00a0/g, ' ').replace(/\r\n/g, '\n');
}

function syncEditableAIState() {
    const briefEl = $('brief-text-display');
    if (briefEl?.isContentEditable) {
        aiState.briefText = getEditableText(briefEl).trim();
    }
    const titleEl = $('draft-title-display');
    if (titleEl?.isContentEditable) {
        aiState.draftTitle = getEditableText(titleEl).replace(/\n+/g, ' ').trim();
    }
    const bodyEl = $('draft-body-display');
    if (bodyEl?.isContentEditable) {
        aiState.draftBody = getEditableText(bodyEl).trim();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadData();
    setupEvents();
});

async function loadData() {
    try {
        const [prod, brand, persona, camp, brandImg] = await Promise.all([
            fetch('../data/products.json').then(r => r.json()),
            fetch('../data/brand_stories.json').then(r => r.json()),
            fetch('../data/personas.json').then(r => r.json()),
            fetch('../data/campaign_events.json').then(r => r.json()),
            fetch('./brand_images.json').then(r => r.json())
        ]);
        PRODUCTS = prod; BRANDS_DATA = brand; PERSONAS = persona; CAMPAIGN_EVENTS = camp; BRAND_IMAGES = brandImg;
        // Render both brand grids so they're ready for either mode
        renderBrands(false);
        renderBrands(true);
    } catch (e) { console.error('Data load error:', e); renderBrands(false); renderBrands(true); }
}

function setupEvents() {
    $('back-btn').onclick = prevStep;
    $('next-btn').onclick = nextStep;

    $('stage-chips').onclick = e => {
        if (!e.target.classList.contains('chip') || e.target.classList.contains('add-custom-btn')) return;
        document.querySelectorAll('#stage-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        state.stageIndex = +e.target.dataset.value;
        updateCampaignInfo(); updateSidebar();
    };

    $('event-chips').onclick = e => {
        if (!e.target.classList.contains('chip')) return;
        document.querySelectorAll('#event-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        selectEvent(e.target.dataset.event);
    };

    $('style-chips').onclick = e => {
        if (!e.target.classList.contains('chip') || e.target.classList.contains('add-custom-btn')) return;
        document.querySelectorAll('#style-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        state.styleIndex = +e.target.dataset.value;
        updateSidebar();
    };

    $('s1-model-chips').onclick = e => {
        if (!e.target.classList.contains('chip')) return;
        document.querySelectorAll('#s1-model-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        $('qwen-model-input').value = e.target.dataset.model;
    };

    $('s2-model-chips').onclick = e => {
        if (!e.target.classList.contains('chip')) return;
        document.querySelectorAll('#s2-model-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        $('exa-model-input').value = e.target.dataset.model;
    };

    // Clear active chips when user types manually
    $('qwen-model-input').oninput = () => {
        document.querySelectorAll('#s1-model-chips .chip').forEach(c => c.classList.remove('active'));
    };
    $('exa-model-input').oninput = () => {
        document.querySelectorAll('#s2-model-chips .chip').forEach(c => c.classList.remove('active'));
    };

    document.addEventListener('click', e => {
        if (e.target.classList.contains('category-tab')) {
            document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            renderProducts(e.target.dataset.category);
        }
    });

    const bindEditable = (id, onChange) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener('input', () => onChange(el));
        el.addEventListener('blur', () => onChange(el));
    };

    bindEditable('brief-text-display', el => {
        aiState.briefText = getEditableText(el).trim();
        updateSidebar();
    });
    bindEditable('draft-title-display', el => {
        aiState.draftTitle = getEditableText(el).replace(/\n+/g, ' ').trim();
        updateSidebar();
    });
    bindEditable('draft-body-display', el => {
        aiState.draftBody = getEditableText(el).trim();
    });
}

function selectMode(mode) {
    state.mode = mode;
    $('mode-selection-screen').style.opacity = '0';
    setTimeout(() => {
        $('mode-selection-screen').style.display = 'none';
        $('main-app').style.display = 'grid';
        $('current-mode-badge').textContent = mode === 'simple' ? '간편 모드' : '전문가 모드';

        if (mode === 'expert') {
            $('simple-brand-view').style.display = 'none';
            $('expert-brand-view').style.display = 'block';
            $('expert-info-panel').style.display = 'block';
            $('expert-persona-creator').style.display = 'block';
            renderBrands(true);
        } else {
            $('simple-brand-view').style.display = 'block';
            $('expert-brand-view').style.display = 'none';
            renderBrands(false);
        }
    }, 200);
}

function goHome() { location.reload(); }

function renderBrands(isExpert = false) {
    const brands = Object.keys(BRANDS_DATA);
    const container = isExpert ? $('expert-brand-grid-list') : $('brand-grid');

    container.innerHTML = brands.map(b => {
        const info = BRAND_IMAGES[b] || {};
        const color = info.color || '#3182F6';
        const logo = info.logo_url || '';
        const eng = info.name_en || '';
        return `
            <div class="brand-card" data-brand="${b}" onclick="selectBrand('${b}')">
                <div class="brand-logo-circle" style="background: ${logo ? 'white' : color}; border: 1px solid #eee;">
                    ${logo ? `<img src="${logo}" alt="${b}" onerror="this.parentElement.innerHTML='${b[0]}'; this.parentElement.style.background='${color}'; this.parentElement.style.color='white';">` : `<span style="color:white;font-weight:700;font-size:18px;">${b[0]}</span>`}
                </div>
                <div class="brand-name">${b}</div>
                <div class="brand-name-en">${eng}</div>
            </div>
        `;
    }).join('');
}

function renderProducts(cat = 'all') {
    if (!state.selectedBrand) return;

    const brandProds = PRODUCTS.filter(p => p.brand_name === state.selectedBrand);
    const cats = [...new Set(brandProds.map(p => p.sub_category || p.category).filter(Boolean))];

    const tabsEl = state.mode === 'expert' ? $('expert-category-tabs') : $('category-tabs');
    tabsEl.innerHTML = `<button class="category-tab ${cat === 'all' ? 'active' : ''}" data-category="all">전체</button>` +
        cats.slice(0, 4).map(c => `<button class="category-tab ${cat === c ? 'active' : ''}" data-category="${c}">${c}</button>`).join('');

    const filtered = cat === 'all' ? brandProds : brandProds.filter(p => (p.sub_category || p.category) === cat);
    const listEl = state.mode === 'expert' ? $('expert-product-list') : $('product-list');

    if (!filtered.length) { listEl.innerHTML = '<p style="padding:20px;color:#888;">제품 없음</p>'; return; }

    listEl.innerHTML = filtered.slice(0, 12).map(p => {
        const img = p.image_urls?.[0] || '';
        const price = parseInt(p.price) || 0;
        return `
            <div class="product-item ${state.selectedProduct?.product_id === p.product_id ? 'selected' : ''}" onclick="selectProduct('${p.product_id}')">
                <div class="product-thumb">${img ? `<img src="${img}" onerror="this.style.display='none'">` : ''}</div>
                <div class="product-info">
                    <div class="product-name">${p.name}</div>
                    <div class="product-price">₩${price.toLocaleString()}</div>
                </div>
            </div>
        `;
    }).join('');
}

function updateCampaignInfo() {
    const eventChipsEl = $('event-chips');
    if (!eventChipsEl) return;
    const selected = state.selectedEvent ? '1' : '0';
    eventChipsEl.innerHTML = `
        <button class=\"chip ${selected === '0' ? 'active' : ''}\" data-event=\"0\">&#xc774;&#xbc24;&#xd2b8; &#xc5c6;&#xc74c;</button>
        <button class=\"chip ${selected === '1' ? 'active' : ''}\" data-event=\"1\">&#xc774;&#xbc24;&#xd2b8; &#xc788;&#xc74c;</button>
    `;
}



function selectEvent(value) {
    state.selectedEvent = value === '1';
    updateCampaignInfo();
    updateSidebar();
}


function updateSidebar() {
    $('sidebar-brand').textContent = state.selectedBrand || '선택 필요';
    $('sidebar-product').textContent = state.selectedProduct?.name?.substring(0, 15) || '-';

    // Only show settings if they've been selected
    let settingsText = '-';
    if (state.stageIndex !== null && state.styleIndex !== null) {
        const stageName = AARRR[state.stageIndex];
        const styleName = STYLES_KR[state.styleIndex]; // Assuming templateTypeKR and templateOrder are defined elsewhere if needed
        $('sidebar-settings').innerText = `${stageName} · ${styleName}`;
    } else {
        $('sidebar-settings').innerText = '-';
    }

    // Step 4: Model
    const s1 = $('qwen-model-input')?.value || 'Auto';
    const s2 = $('exa-model-input')?.value || 'Auto';
    if (state.currentStep > 4) {
        $('sidebar-model').innerText = `${s1.split('/').pop()} / ${s2.split('/').pop()}`;
    } else {
        $('sidebar-model').innerText = '-';
    }

    // AI Step status updates
    if ($('sidebar-brief')) {
        $('sidebar-brief').textContent = aiState.briefText ? '완료 ✓' : '-';
    }
    if ($('sidebar-draft')) {
        $('sidebar-draft').textContent = aiState.draftTitle ? '완료 ✓' : '-';
    }
    if ($('sidebar-result')) {
        $('sidebar-result').textContent = aiState.tunedMessages?.length > 0 ? `${aiState.tunedMessages.length}개` : '-';
    }

    document.querySelectorAll('.progress-step').forEach(s => {
        const n = +s.dataset.step;
        s.classList.toggle('active', n === state.currentStep);
        s.classList.toggle('completed', n < state.currentStep);

        // Disable steps that haven't been reached yet (for AI steps)
        if (n > 4) { // AI steps now start from 5
            const canNavigate = canNavigateToAIStep(n);
            s.classList.toggle('disabled', !canNavigate);
        }
    });

    // Step-specific navigation logic
    let canNext = false;
    if (state.currentStep === 1 && state.selectedBrand) canNext = true;
    if (state.currentStep === 2 && state.selectedProduct) canNext = true;
    if (state.currentStep === 3 && state.stageIndex !== null && state.styleIndex !== null) canNext = true;
    if (state.currentStep === 4) canNext = true; // Model selection
    if (state.currentStep === 5) canNext = true; // Brief 확인
    if (state.currentStep === 6) canNext = true; // Draft 확인
    if (state.currentStep === 7) canNext = false; // 마지막
    $('next-btn').disabled = !canNext;
    $('back-btn').disabled = state.currentStep === 1;

    // Update next button text based on step
    if (state.currentStep === 4) $('next-btn').textContent = '브리프 생성';
    else if (state.currentStep === 5) $('next-btn').textContent = '초안 생성';
    else if (state.currentStep === 6) $('next-btn').textContent = '메시지 생성';
    else if (state.currentStep === 7) $('next-btn').textContent = '완료';
    else $('next-btn').textContent = '다음';
}

function selectBrand(b) {
    state.selectedBrand = b;
    document.querySelectorAll('.brand-card').forEach(c => c.classList.toggle('selected', c.dataset.brand === b));
    $('selected-brand-name').textContent = b;

    if (state.mode === 'expert') {
        $('custom-brand-name').value = b;
        $('custom-brand-story').value = BRANDS_DATA[b]?.story || '';
    }
    updateSidebar();
}

function selectProduct(id) {
    state.selectedProduct = PRODUCTS.find(p => p.product_id === id);

    if (state.mode === 'expert' && state.selectedProduct) {
        $('custom-product-name').value = state.selectedProduct.name;
        $('custom-product-price').value = state.selectedProduct.price;
    }

    renderProducts(document.querySelector('.category-tab.active')?.dataset.category || 'all');
    updateSidebar();
}

// Sidebar navigation helper functions
function canNavigateToAIStep(step) {
    // Can navigate to AI steps only if they have data
    if (step === 5) return aiState.briefText !== ''; // Brief is now step 5
    if (step === 6) return aiState.draftTitle !== ''; // Draft is now step 6
    if (step === 7) return aiState.tunedMessages?.length > 0; // Result is now step 7
    return true; // Steps 1-4 always navigable
}

function navigateToStep(targetStep) {
    // For AI steps (5-7), check if they have data
    if (targetStep > 4 && !canNavigateToAIStep(targetStep)) {
        return; // Can't navigate to steps without data
    }

    // Can always go back to earlier steps
    if (targetStep <= state.currentStep) {
        goToStep(targetStep);
        return;
    }

    // For forward navigation, use normal flow
    if (targetStep === state.currentStep + 1) {
        if (targetStep === 5) { // From Model to Brief
            generateBrief();
        } else if (targetStep === 6) { // From Brief to Draft
            generateDraftFromBrief();
        } else if (targetStep === 7) { // From Draft to Result
            generateTuningFromDraft(); // This was generateTuningFromDraft, not renderPhoneMockupsFromAPI directly
        } else {
            nextStep(); // For non-AI steps
        }
    }
}

window.updateLoadingStep = function (index, status) {
    const el = $(`load-step-${index + 1}`);
    if (!el) return;
    el.classList.remove('active', 'done');
    if (status) el.classList.add(status);
};

function nextStep() {
    if (state.currentStep === 4) { generateBrief(); return; }
    if (state.currentStep === 5) { generateDraftFromBrief(); return; }
    if (state.currentStep === 6) { generateTuningFromDraft(); return; }
    if (state.currentStep === 7) { return; }
    goToStep(state.currentStep + 1);
}

function prevStep() { if (state.currentStep > 1) goToStep(state.currentStep - 1); }

function goToStep(step) {
    document.querySelectorAll('.step-section').forEach((el, i) => el.classList.toggle('active', i === step - 1));
    state.currentStep = step;

    if (step === 2 && state.selectedBrand) {
        if (state.mode === 'expert') {
            $('expert-product-view').style.display = 'block';
            $('simple-product-view').style.display = 'none';
        } else {
            $('expert-product-view').style.display = 'none';
            $('simple-product-view').style.display = 'block';
        }
        renderProducts('all');
    }
    if (step === 3) {
        // Show expert creator panel in expert mode
        if (state.mode === 'expert') {
            $('expert-persona-creator').style.display = 'block';
        } else {
            $('expert-persona-creator').style.display = 'none';
        }
        updateCampaignInfo();
    }
    updateSidebar();
}

// ------------------------------------------------------------------
// Real AI Pipeline (Backend API Integration)
// ------------------------------------------------------------------

// Store AI results
let aiState = {
    briefText: '',
    draftTitle: '',
    draftBody: '',
    tunedMessages: []
};

async function generateBrief() {
    // Step 4에서 호출 → Step 5 (Brief 생성)로 이동
    const overlay = $('loading-overlay');
    overlay.style.display = 'flex';

    try {
        // Step 1 API: Brief 생성
        updateLoadingStep(0, 'active');

        const eventInfo = state.selectedEvent ? {
            name: state.selectedEvent.name,
            detail: state.selectedEvent.detail
        } : null;

        const briefResult = await CRMStudioAPI.generateBrief(
            state.selectedBrand,
            state.selectedProduct?.name || '',
            state.stageIndex || 0,
            state.styleIndex || 0,
            eventInfo,
            $('qwen-model-input')?.value || state.qwenModel
        );

        updateLoadingStep(0, 'done');

        aiState.briefText = briefResult.data.brief_text;

        overlay.style.display = 'none';

        // Step 5로 이동 (Brief 확인)
        $('brief-text-display').textContent = aiState.briefText;
        goToStep(5);

    } catch (error) {
        overlay.style.display = 'none';
        alert('브리프 생성 실패: ' + error.message);
        console.error(error);
    }
}

async function regenerateBrief() {
    syncEditableAIState();
    const feedback = $('brief-feedback-input').value.trim();
    if (!feedback) {
        alert('수정 요청을 입력해주세요');
        return;
    }

    $('brief-result-card').classList.add('loading');
    $('brief-text-display').textContent = '재생성 중...';

    try {
        const result = await CRMStudioAPI.refineBrief(aiState.briefText, feedback);
        aiState.briefText = result.data.brief_text;
        $('brief-text-display').textContent = aiState.briefText;
        $('brief-feedback-input').value = '';
    } catch (error) {
        alert('재생성 실패: ' + error.message);
    } finally {
        $('brief-result-card').classList.remove('loading');
    }
}

async function generateDraftFromBrief() {
    // Step 4 → Step 5 (Draft 생성)
    syncEditableAIState();
    const overlay = $('loading-overlay');
    overlay.style.display = 'flex';

    try {
        updateLoadingStep(1, 'active');

        const s1Model = $('qwen-model-input')?.value || state.qwenModel;
        const result = await CRMStudioAPI.generateDraft(aiState.briefText, s1Model);

        updateLoadingStep(1, 'done');

        aiState.draftTitle = result.data.title;
        aiState.draftBody = result.data.body;

        overlay.style.display = 'none';

        // Step 6로 이동 (Draft 확인)
        $('draft-title-display').textContent = aiState.draftTitle;
        $('draft-body-display').textContent = aiState.draftBody;
        $('brand-tone-display').textContent = (result.data.brand_tone || []).join(', ');
        goToStep(6);

    } catch (error) {
        overlay.style.display = 'none';
        alert('초안 생성 실패: ' + error.message);
        console.error(error);
    }
}

async function regenerateDraft() {
    syncEditableAIState();
    const feedback = $('draft-feedback-input').value.trim();
    if (!feedback) {
        alert('수정 요청을 입력해주세요');
        return;
    }

    $('draft-result-card').classList.add('loading');

    try {
        const result = await CRMStudioAPI.refineDraft(
            { title: aiState.draftTitle, body: aiState.draftBody },
            feedback
        );
        aiState.draftTitle = result.data.title;
        aiState.draftBody = result.data.body;
        $('draft-title-display').textContent = aiState.draftTitle;
        $('draft-body-display').textContent = aiState.draftBody;
        $('draft-feedback-input').value = '';
    } catch (error) {
        alert('재생성 실패: ' + error.message);
    } finally {
        $('draft-result-card').classList.remove('loading');
    }
}

async function generateTuningFromDraft() {
    // Step 5 → Step 6 (Tuning 생성)
    syncEditableAIState();
    const overlay = $('loading-overlay');
    overlay.style.display = 'flex';

    try {
        updateLoadingStep(2, 'active');
        updateLoadingStep(3, 'active');

        const s2Model = $('exa-model-input')?.value || state.exaModel;
        const result = await CRMStudioAPI.generateTuning({
            title: aiState.draftTitle,
            body: aiState.draftBody
        }, null, s2Model);

        updateLoadingStep(2, 'done');
        updateLoadingStep(3, 'done');

        aiState.tunedMessages = result.data.messages;

        overlay.style.display = 'none';

        // Step 7으로 이동 (결과)
        await renderPhoneMockupsFromAPI();
        goToStep(7);

    } catch (error) {
        overlay.style.display = 'none';
        alert('페르소나 튜닝 실패: ' + error.message);
        console.error(error);
    }
}

async function renderPhoneMockupsFromAPI() {
    let generatedMap = {};

    if (aiState.tunedMessages && aiState.tunedMessages.length > 0) {
        // Use already tuned messages
        aiState.tunedMessages.forEach(m => {
            if (m.message) {
                generatedMap[m.persona] = splitMessage(m.message, state.selectedBrand);
                return;
            }
            const title = (m.title || '').trim();
            const body = (m.body || '').trim();
            generatedMap[m.persona] = {
                title: title || `[${state.selectedBrand}] 메시지`,
                body
            };
        });
    } else {
        // Fallback to batch API if needed
        try {
            generatedMap = await requestGeneratedMessages();
        } catch (e) {
            console.error('Generate API error:', e);
        }
    }

    const overlay = $('loading-overlay');
    if (overlay) overlay.style.display = 'none';
    renderPhoneMockups(generatedMap);
}


function splitMessage(text, brand) {
    const cleaned = String(text || '').trim();
    if (!cleaned) {
        return { title: `[${brand}] \uba54\uc2dc\uc9c0`, body: '' };
    }
    const parts = cleaned.split('\n').map(p => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
        return { title: parts[0], body: parts.slice(1).join('\n') };
    }
    return { title: `[${brand}] \uba54\uc2dc\uc9c0`, body: cleaned };
}

async function requestGeneratedMessages() {
    if (!API_ENDPOINT) {
        throw new Error('API base is not configured');
    }
    if (!state.selectedBrand || !state.selectedProduct || state.stageIndex === null || state.styleIndex === null) {
        return null;
    }
    if (!state.selectedProduct.product_id) {
        return null;
    }
    const stage1Model = $('qwen-model-input')?.value || state.qwenModel;
    const stage2Model = $('exa-model-input')?.value || state.exaModel;

    const items = PERSONAS.map((p, idx) => ({
        persona: idx,
        brand: state.selectedBrand,
        product: state.selectedProduct.name,
        stage_index: state.stageIndex,
        style_index: state.styleIndex,
        is_event: state.selectedEvent ? 1 : 0,
        stage1_model: stage1Model,
        stage2_model: stage2Model
    }));
    const res = await fetch(API_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
    });
    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || res.statusText);
    }
    const data = await res.json();
    const results = data.results || [];
    const map = {};
    results.forEach((result, idx) => {
        const personaName = PERSONAS[idx]?.name || result?.persona_profile?.name;
        // Generic parsing: try stage2, then exaone, then crm_message
        const message = result?.stage2?.result_raw || result?.exaone?.result_raw || result?.crm_message;
        if (personaName && message) {
            map[personaName] = splitMessage(message, state.selectedBrand);
        }
    });
    return map;
}

function renderPhoneMockups(generatedMap) {
    const brand = state.selectedBrand;
    const info = BRAND_IMAGES[brand] || {};
    const color = info.color || '#3182F6';
    const logo = info.logo_url || '';
    const product = state.selectedProduct?.name || '제품';
    const price = state.selectedProduct?.price ? parseInt(state.selectedProduct.price).toLocaleString() : '';
    const eventLabel = state.selectedEvent ? '\uc774\ubca4\ud2b8' : '\uc624\ub298\ub9cc';

    // Realistic persona-specific messages
    const personaMessages = {
        'Luxury_Lover': {
            title: `[${brand}] VIP 고객님을 위한 특별 제안`,
            body: `프리미엄 ${product}을 먼저 만나보세요.\n지금 구매 시 럭셔리 샘플 3종 증정 💎`
        },
        '재구매': { // Retention
            title: `[${brand}] ${product} 잘 사용하고 계신가요?`,
            body: `고객님을 위한 재구매 전용 혜택이 도착했어요.\n한 번 더 경험하는 ${brand}의 감동,\n지금 멤버십 혜택으로 만나보세요.`
        },
        'Budget_Seeker': {
            title: `[${brand}] ${eventLabel} 특가!`,
            body: `${product} ${price ? `정가 ₩${price}` : ''}\n지금 20% 할인 + 무료배송 ✨`
        },
        '추천': { // Referral
            title: `[${brand}] 좋은 건 함께 나누세요 💖`,
            body: `친구에게 ${product} 추천하고\n두 분 모두에게 10,000 포인트 적립!\n함께 예뻐지는 뷰티 루틴.`
        },
        'Custom': {
            title: `[${brand}] 고객님을 위한 맞춤 제안`,
            body: `${product}의 특별한 혜택을 확인해보세요.\n${state.selectedEvent ? state.selectedEvent.name + ' 기념' : ''} 특별 프로모션 진행 중!`
        }
    };

    const msgs = PERSONAS.map(p => {
        const generated = generatedMap && generatedMap[p.name];
        const fallback = personaMessages[p.name] || { title: `[${brand}] \uba54\uc2dc\uc9c0`, body: `${product} \uc9c0\uae08 \ud655\uc778\ud558\uc138\uc694` };
        return {
            name: p.name,
            ...PERSONA_INFO[p.name],
            ...(generated || fallback)
        };
    });

    const baseTmpl = personaMessages.Custom || { title: `[${brand}] 메시지`, body: `${product} 지금 확인하세요` };

    // Add custom personas with generic logic
    state.customPersonas.forEach(p => {
        msgs.push({
            name: p.name,
            label: '커스텀',
            bg: '#F4F0F7',
            color: '#9065B0',
            title: `[${p.name}님] ${baseTmpl.title}`,
            body: baseTmpl.body + (p.keywords ? `\n\n키워드 반영: ${p.keywords}` : '')
        });
    });

    $('phone-carousel').innerHTML = msgs.map(m => `
        <div class="phone-mockup">
            <div class="iphone-frame">
                <div class="iphone-screen">
                    <div style="text-align:right;color:#fff;font-size:13px;margin-bottom:60px;padding-right:8px;">9:41</div>
                    <div class="notif-card">
                        <div class="notif-header">
                            <div class="notif-icon" style="background:${color};">${logo ? `<img src="${logo}" style="width:14px;height:14px;">` : brand[0]}</div>
                            <span class="notif-app">${brand}</span>
                            <span class="notif-time">지금</span>
                        </div>
                        <div class="notif-title">${m.title}</div>
                        <div class="notif-body">${m.body.replace(/\n/g, '<br>')}</div>
                        <div class="persona-badge" style="background:${m.bg};color:${m.color};">${m.label}</div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function resetWizard() {
    state = { currentStep: 1, selectedBrand: null, selectedProduct: null, stageIndex: null, styleIndex: null, selectedEvent: null, mode: state.mode, customData: {} };
    document.querySelectorAll('.brand-card').forEach(c => c.classList.remove('selected'));
    goToStep(1);
}

function exportAll() {
    const data = {
        brand: state.selectedBrand, product: state.selectedProduct,
        stage: AARRR[state.stageIndex], personas: PERSONAS.map(p => p.name),
        generated: new Date().toISOString()
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `crm_${state.selectedBrand}_${Date.now()}.json`;
    a.click();
}

function useCustomBrand() { state.selectedBrand = $('custom-brand-name').value || '커스텀'; updateSidebar(); }
function useCustomProduct() { state.selectedProduct = { name: $('custom-product-name').value, price: $('custom-product-price').value }; updateSidebar(); }
function addCustomPersona() {
    const name = $('new-persona-name').value.trim();
    const keywords = $('new-persona-keywords').value.trim();
    if (!name) { alert('페르소나 이름을 입력해주세요'); return; }

    const id = 'custom_p_' + Date.now();
    const newPersona = { id, name, keywords };
    state.customPersonas.push(newPersona);

    // Clear inputs
    $('new-persona-name').value = '';
    $('new-persona-keywords').value = '';

    renderAddedPersonas();
}

function removeCustomPersona(id) {
    state.customPersonas = state.customPersonas.filter(p => p.id !== id);
    renderAddedPersonas();
}

function renderAddedPersonas() {
    const listEl = $('added-personas-list');
    listEl.innerHTML = state.customPersonas.map(p => `
        <div class="added-item-tag">
            <span>${p.name}</span>
            <span class="remove-btn" onclick="removeCustomPersona('${p.id}')">×</span>
        </div>
    `).join('');
}

function addCustomEvent() {
    const name = $('new-event-name').value.trim();
    const detail = $('new-event-detail').value.trim();
    if (!name) { alert('이벤트 이름을 입력해주세요'); return; }

    const id = 'custom_ev_' + Date.now();
    const newEvent = { id, name, detail };
    state.customEvents.push(newEvent);

    // Clear inputs
    $('new-event-name').value = '';
    $('new-event-detail').value = '';

    renderAddedEvents();
}

function removeCustomEvent(id) {
    state.customEvents = state.customEvents.filter(e => e.id !== id);
    renderAddedEvents();
}
function addCustomStage() {
    const name = $('new-stage-name').value.trim();
    const detail = $('new-stage-detail').value.trim();
    if (!name) { alert('발송 목적 이름을 입력해주세요'); return; }

    const id = 'custom_st_' + Date.now();
    const newStage = { id, name, detail };
    state.customStages.push(newStage);

    // Add to selection arrays
    const newIndex = AARRR_KR.length;
    AARRR_KR.push(name);
    AARRR.push('Custom');

    // Add UI Chip
    const chipsContainer = $('stage-chips');
    // Insert before the "+ 직접 입력" button
    const addButton = chipsContainer.querySelector('.add-custom-btn');
    const newBtn = document.createElement('button');
    newBtn.className = 'chip';
    newBtn.dataset.value = newIndex;
    newBtn.dataset.customId = id; // Track ID
    newBtn.textContent = name;
    chipsContainer.insertBefore(newBtn, addButton);

    // Clear inputs
    $('new-stage-name').value = '';
    $('new-stage-detail').value = '';

    renderAddedStages();
    // Auto select
    newBtn.click();
}

function removeCustomStage(id) {
    state.customStages = state.customStages.filter(s => s.id !== id);
    // Note: Removing from AARRR/AARRR_KR and chips is complex due to index shift.
    // For simplicity in this demo, we allow adding but removal only removes from the "Added List" display and state.
    // Ideally, we'd rebuild the chips, but indices are hardcoded in data-value.
    renderAddedStages();
}

function renderAddedStages() {
    const listEl = $('added-stages-list');
    listEl.innerHTML = state.customStages.map(s => `
        <div class="added-item-tag">
            <span>${s.name}</span>
            <span class="remove-btn" onclick="removeCustomStage('${s.id}')">×</span>
        </div>
    `).join('');
}

function addCustomStyle() {
    const name = $('new-style-name').value.trim();
    const detail = $('new-style-detail').value.trim();
    if (!name) { alert('스타일 이름을 입력해주세요'); return; }

    const id = 'custom_sy_' + Date.now();
    const newStyle = { id, name, detail };
    state.customStyles.push(newStyle);

    // Add to selection arrays
    const newIndex = STYLES_KR.length;
    STYLES_KR.push(name);

    // Add UI Chip
    const chipsContainer = $('style-chips');
    const addButton = chipsContainer.querySelector('.add-custom-btn');
    const newBtn = document.createElement('button');
    newBtn.className = 'chip';
    newBtn.dataset.value = newIndex;
    newBtn.dataset.customId = id;
    newBtn.textContent = name;
    chipsContainer.insertBefore(newBtn, addButton);

    // Clear inputs
    $('new-style-name').value = '';
    $('new-style-detail').value = '';

    renderAddedStyles();
    // Auto select
    newBtn.click();
}

function removeCustomStyle(id) {
    state.customStyles = state.customStyles.filter(s => s.id !== id);
    renderAddedStyles();
}

function renderAddedStyles() {
    const listEl = $('added-styles-list');
    listEl.innerHTML = state.customStyles.map(s => `
        <div class="added-item-tag">
            <span>${s.name}</span>
            <span class="remove-btn" onclick="removeCustomStyle('${s.id}')">×</span>
        </div>
    `).join('');
}
function renderAddedEvents() {
    const listEl = $('added-events-list');
    const chipsEl = $('event-chips');

    // Render in the creator list
    listEl.innerHTML = state.customEvents.map(e => `
        <div class="added-item-tag">
            <span>${e.name}</span>
            <span class="remove-btn" onclick="removeCustomEvent('${e.id}')">×</span>
        </div>
    `).join('');

    // Also update the selection chips if in step 3
    if (state.currentStep === 3) {
        updateCampaignInfo();
    }
}
