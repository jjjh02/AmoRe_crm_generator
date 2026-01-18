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

state = {
    currentStep: 1, selectedBrand: null, selectedProduct: null,
    stageIndex: null, styleIndex: null, selectedEvent: null, mode: 'simple',
    customData: { brandName: '', brandStory: '', productName: '', productPrice: 0 },
    customPersonas: [], customEvents: [], customStages: [], customStyles: []
};

let AARRR = ['Acquisition', 'Activation', 'Retention', 'Revenue', 'Referral'];
let AARRR_KR = ['유입', '구매', '재구매', '매출', '추천'];
let STYLES_KR = ['긴박', '정보', 'FOMO', '감성', '시즌'];

const $ = id => document.getElementById(id);

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

    $('style-chips').onclick = e => {
        if (!e.target.classList.contains('chip') || e.target.classList.contains('add-custom-btn')) return;
        document.querySelectorAll('#style-chips .chip').forEach(c => c.classList.remove('active'));
        e.target.classList.add('active');
        state.styleIndex = +e.target.dataset.value;
        updateSidebar();
    };

    document.addEventListener('click', e => {
        if (e.target.classList.contains('category-tab')) {
            document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            renderProducts(e.target.dataset.category);
        }
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
    if (state.stageIndex === null) return;

    const stage = AARRR[state.stageIndex];
    const stageData = CAMPAIGN_EVENTS[stage];
    if (!stageData) return;

    // Get promotion events (promotion_y has promotions)
    const promoEvents = stageData.promotion_y || [];
    const nonPromoEvents = stageData.promotion_n || [];
    const allEvents = [...promoEvents, ...nonPromoEvents, ...state.customEvents];

    // Render event chips
    const eventChipsEl = $('event-chips');
    if (eventChipsEl) {
        eventChipsEl.innerHTML = allEvents.map((ev, i) => `
            <span class="chip ${state.selectedEvent?.id === ev.id ? 'active' : ''}" 
                  data-event-id="${ev.id}" onclick="selectEvent('${ev.id}')">${ev.name}</span>
        `).join('');
    }

    // Show event detail if selected
    const detailBox = $('event-detail-box');
    if (detailBox && state.selectedEvent) {
        detailBox.innerHTML = `
            <div class="info-row"><span class="label">이벤트</span><span class="val">${state.selectedEvent.name}</span></div>
            <div class="info-row"><span class="label">상세</span><span class="val desc">${state.selectedEvent.detail}</span></div>
        `;
        detailBox.style.display = 'block';
    } else if (detailBox) {
        detailBox.innerHTML = '<p style="color:#8B95A1;font-size:13px;">목적 선택 시 표시됩니다</p>';
    }
}

function selectEvent(eventId) {
    const stage = AARRR[state.stageIndex];
    const stageData = CAMPAIGN_EVENTS[stage];
    const allEvents = [...(stageData?.promotion_y || []), ...(stageData?.promotion_n || []), ...state.customEvents];
    state.selectedEvent = allEvents.find(e => e.id === eventId);
    updateCampaignInfo();
    updateSidebar();
}

function updateSidebar() {
    $('sidebar-brand').textContent = state.selectedBrand || '선택 필요';
    $('sidebar-product').textContent = state.selectedProduct?.name?.substring(0, 15) || '-';

    // Only show settings if they've been selected
    let settingsText = '-';
    if (state.stageIndex !== null && state.styleIndex !== null) {
        settingsText = `${AARRR_KR[state.stageIndex]} · ${STYLES_KR[state.styleIndex]}`;
    } else if (state.stageIndex !== null) {
        settingsText = AARRR_KR[state.stageIndex];
    }
    $('sidebar-settings').textContent = settingsText;

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
        if (n > 3) {
            const canNavigate = canNavigateToAIStep(n);
            s.classList.toggle('disabled', !canNavigate);
        }
    });

    // Step-specific navigation logic
    let canNext = false;
    if (state.currentStep === 1 && state.selectedBrand) canNext = true;
    if (state.currentStep === 2 && state.selectedProduct) canNext = true;
    if (state.currentStep === 3 && state.stageIndex !== null && state.styleIndex !== null) canNext = true;
    if (state.currentStep === 4) canNext = true; // Brief 확인
    if (state.currentStep === 5) canNext = true; // Draft 확인
    if (state.currentStep === 6) canNext = false; // 마지막
    $('next-btn').disabled = !canNext;
    $('back-btn').disabled = state.currentStep === 1;

    // Update next button text based on step
    if (state.currentStep === 3) $('next-btn').textContent = '브리프 생성';
    else if (state.currentStep === 4) $('next-btn').textContent = '초안 생성';
    else if (state.currentStep === 5) $('next-btn').textContent = '메시지 생성';
    else if (state.currentStep === 6) $('next-btn').textContent = '완료';
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
    if (step === 4) return aiState.briefText !== '';
    if (step === 5) return aiState.draftTitle !== '';
    if (step === 6) return aiState.tunedMessages?.length > 0;
    return true; // Steps 1-3 always navigable
}

function navigateToStep(targetStep) {
    // For AI steps (4-6), check if they have data
    if (targetStep > 3 && !canNavigateToAIStep(targetStep)) {
        return; // Can't navigate to steps without data
    }

    // Can always go back to earlier steps
    if (targetStep <= state.currentStep) {
        goToStep(targetStep);
        return;
    }

    // For forward navigation, use normal flow
    if (targetStep === state.currentStep + 1) {
        nextStep();
    }
}

function nextStep() {
    if (state.currentStep === 3) { generateMessages(); return; }
    if (state.currentStep === 4) { generateDraftFromBrief(); return; }
    if (state.currentStep === 5) { generateTuningFromDraft(); return; }
    if (state.currentStep === 6) { return; } // 마지막 단계
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

async function generateMessages() {
    // Step 3에서 호출 → Step 4 (Brief 생성)로 이동
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
            eventInfo
        );

        updateLoadingStep(0, 'done');

        aiState.briefText = briefResult.data.brief_text;

        overlay.style.display = 'none';

        // Step 4로 이동 (Brief 확인)
        $('brief-text-display').textContent = aiState.briefText;
        goToStep(4);

    } catch (error) {
        overlay.style.display = 'none';
        alert('브리프 생성 실패: ' + error.message);
        console.error(error);
    }
}

async function regenerateBrief() {
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
    const overlay = $('loading-overlay');
    overlay.style.display = 'flex';

    try {
        updateLoadingStep(1, 'active');

        const result = await CRMStudioAPI.generateDraft(aiState.briefText);

        updateLoadingStep(1, 'done');

        aiState.draftTitle = result.data.title;
        aiState.draftBody = result.data.body;

        overlay.style.display = 'none';

        // Step 5로 이동 (Draft 확인)
        $('draft-title-display').textContent = aiState.draftTitle;
        $('draft-body-display').textContent = aiState.draftBody;
        $('brand-tone-display').textContent = (result.data.brand_tone || []).join(', ');
        goToStep(5);

    } catch (error) {
        overlay.style.display = 'none';
        alert('초안 생성 실패: ' + error.message);
        console.error(error);
    }
}

async function regenerateDraft() {
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
    const overlay = $('loading-overlay');
    overlay.style.display = 'flex';

    try {
        updateLoadingStep(2, 'active');
        updateLoadingStep(3, 'active');

        const result = await CRMStudioAPI.generateTuning({
            title: aiState.draftTitle,
            body: aiState.draftBody
        });

        updateLoadingStep(2, 'done');
        updateLoadingStep(3, 'done');

        aiState.tunedMessages = result.data.messages;

        overlay.style.display = 'none';

        // Step 6으로 이동 (결과)
        renderPhoneMockupsFromAPI();
        goToStep(6);

    } catch (error) {
        overlay.style.display = 'none';
        alert('페르소나 튜닝 실패: ' + error.message);
        console.error(error);
    }
}

function renderPhoneMockupsFromAPI() {
    const brand = state.selectedBrand;
    const info = BRAND_IMAGES[brand] || {};
    const color = info.color || '#3182F6';
    const logo = info.logo_url || '';

    $('phone-carousel').innerHTML = aiState.tunedMessages.map(m => `
        <div class="phone-mockup">
            <div class="iphone-frame">
                <div class="iphone-screen">
                    <div style="text-align:right;color:#fff;font-size:13px;margin-bottom:60px;padding-right:8px;">9:41</div>
                    <div class="notif-card">
                        <div class="notif-header">
                            <div class="notif-icon" style="background:${m.color || color};">${logo ? `<img src="${logo}" style="width:14px;height:14px;">` : brand[0]}</div>
                            <span class="notif-app">${brand}</span>
                            <span class="notif-time">지금</span>
                        </div>
                        <div class="notif-title">${m.title}</div>
                        <div class="notif-body">${m.body.replace(/\n/g, '<br>')}</div>
                        <div class="persona-badge" style="background:${PERSONA_INFO[m.persona]?.bg || '#F4F0F7'};color:${m.color};">${m.label}</div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function updateLoadingStep(index, status) {
    const steps = ['load-step-1', 'load-step-2', 'load-step-3', 'load-step-4'];
    const id = steps[index];
    if ($(id)) {
        $(id).classList.add(status);
        if (status === 'active') {
            $(id).style.fontWeight = 'bold';
        }
    }
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

function renderPhoneMockups() {
    const brand = state.selectedBrand;
    const info = BRAND_IMAGES[brand] || {};
    const color = info.color || '#3182F6';
    const logo = info.logo_url || '';
    const product = state.selectedProduct?.name || '제품';
    const priceStr = state.selectedProduct?.price ? parseInt(state.selectedProduct.price).toLocaleString() : '';
    const stage = AARRR_KR[state.stageIndex] || '일반';
    const style = STYLES_KR[state.styleIndex] || '정보형';

    // --- Smart Templates based on AARRR Stage ---
    const templates = {
        '유입': { // Acquisition
            title: `[${brand}] 첫 만남을 위한 특별한 선물 🎁`,
            body: `${product}을(를) 경험해보세요.\n신규 회원 가입 시 웰컴 키트 증정!\n지금 바로 확인하기 👉`
        },
        '구매': { // Activation
            title: `[${brand}] 망설이셨던 ${product}, 지금이 기회!`,
            body: `단 3일간 진행되는 시크릿 혜택.\n${priceStr ? `정가 ₩${priceStr} → ` : ''}최대 15% 추가 할인 쿠폰 도착 💌\n품절 전에 만나보세요.`
        },
        '재구매': { // Retention
            title: `[${brand}] ${product} 잘 사용하고 계신가요?`,
            body: `고객님을 위한 재구매 전용 혜택이 도착했어요.\n한 번 더 경험하는 ${brand}의 감동,\n지금 멤버십 혜택으로 만나보세요.`
        },
        '매출': { // Revenue (Upselling)
            title: `[${brand}] ${product}와 함께하면 더 좋은 아이템`,
            body: `함께 쓰면 시너지 200%! ✨\n${brand} 베스트 셀러 듀오 세트를\nVIP 특별가로 준비했습니다.`
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

    // Style Adjustments (Tone)
    const toneModifiers = {
        '긴박': (t) => ({ title: `⏳ 마감 임박! ${t.title}`, body: `오늘 자정 종료! ${t.body}` }),
        '정보': (t) => ({ title: `ℹ️ ${t.title}`, body: `${product} 핵심 성분 분석.\n${t.body}` }),
        '감성': (t) => ({ title: `🌿 ${t.title}`, body: `당신의 일상을 빛내줄 ${product}.\n${t.body}` }),
        '시즌': (t) => ({ title: `🍂 시즌 추천 ${t.title}`, body: `지금 계절에 딱 맞는 선택.\n${t.body}` }),
        'FOMO': (t) => ({ title: `🔥 주문 폭주 ${t.title}`, body: `남은 수량이 얼마 없어요!\n${t.body}` })
    };

    let baseTmpl = templates[stage] || templates['Custom'];

    // Apply Tone Modifier if exists
    if (toneModifiers[style]) {
        baseTmpl = toneModifiers[style](baseTmpl);
    }

    // Persona Variations (Applying base logic + Persona flavor)
    const personaMessages = PERSONAS.map(p => {
        let pTitle = baseTmpl.title;
        let pBody = baseTmpl.body;

        // Custom tweaks per persona
        if (p.name === 'Luxury_Lover') {
            pTitle = `💎 VIP Only: ${pTitle}`;
            pBody = pBody + `\n프리미엄 패키징 무료 업그레이드.`;
        } else if (p.name === 'Sensitive_Skin') {
            pBody = `민감한 피부도 안심.\n` + pBody;
        } else if (p.name === 'Budget_Seeker') {
            pTitle = `💰 최대 혜택: ${pTitle}`;
        } else if (p.name === 'Trend_Follower') {
            pTitle = `🔥 SNS 화제: ${pTitle}`;
            pBody = `#${brand.replace(/ /g, '')} #${product.replace(/ /g, '')}\n` + pBody;
        }

        return {
            name: p.name,
            ...PERSONA_INFO[p.name],
            title: pTitle,
            body: pBody
        };
    });

    // Add custom personas with generic logic
    state.customPersonas.forEach(p => {
        personaMessages.push({
            name: p.name,
            label: '커스텀',
            bg: '#F4F0F7',
            color: '#9065B0',
            title: `[${p.name}님] ${baseTmpl.title}`,
            body: baseTmpl.body + (p.keywords ? `\n\n키워드 반영: ${p.keywords}` : '')
        });
    });

    $('phone-carousel').innerHTML = personaMessages.map(m => `
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
