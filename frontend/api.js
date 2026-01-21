/**
 * CRM Message Studio - API 통신 모듈
 * 백엔드 3단계 파이프라인 API 연동
 * v2.0 - 모델 선택 및 페르소나 선택 지원
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// 현재 세션 ID 저장
let currentSessionId = null;

// 현재 모델 설정 (각 단계별)
let modelSettings = {
    brief: { provider: null, model: null },
    draft: { provider: null, model: null },
    tuning: { provider: null, model: null }
};

// 사용 가능한 모델 목록 캐시
let availableModels = null;

/**
 * API 에러 처리
 */
class APIError extends Error {
    constructor(message, code, details) {
        super(message);
        this.code = code;
        this.details = details;
    }
}

/**
 * 공통 fetch 래퍼
 */
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };

    try {
        const response = await fetch(url, config);
        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new APIError(
                data.error?.message || '알 수 없는 오류가 발생했습니다',
                data.error?.code || 'UNKNOWN_ERROR',
                data.error?.details
            );
        }

        return data;
    } catch (error) {
        if (error instanceof APIError) throw error;
        throw new APIError('서버와 통신할 수 없습니다', 'NETWORK_ERROR', error.message);
    }
}

// ===========================
// Model & Provider API
// ===========================

/**
 * 사용 가능한 모델 목록 조회
 */
async function getAvailableModels() {
    if (availableModels) return availableModels;
    
    try {
        const result = await apiRequest('/models');
        availableModels = result.data;
        return availableModels;
    } catch (error) {
        console.error('모델 목록 조회 실패:', error);
        return { providers: [], default_provider: 'ollama' };
    }
}

/**
 * 페르소나 목록 조회
 */
async function getPersonas() {
    try {
        const result = await apiRequest('/personas');
        return result.data.personas;
    } catch (error) {
        console.error('페르소나 목록 조회 실패:', error);
        return [];
    }
}

/**
 * 모델 설정 저장
 */
function setModelConfig(step, provider, model) {
    modelSettings[step] = { provider, model };
}

/**
 * 모델 설정 가져오기
 */
function getModelConfig(step) {
    const config = modelSettings[step];
    if (config && (config.provider || config.model)) {
        return config;
    }
    return null;
}

// ===========================
// Step 1: Brief API
// ===========================

/**
 * Step 1: 마케팅 브리프 생성
 */
async function generateBrief(brandName, productName, stageIndex, styleIndex, event = null, customStageName = null, customStyleName = null) {
    const body = {
        brand_name: brandName,
        product_name: productName,
        stage_index: stageIndex,
        style_index: styleIndex
    };

    if (event) {
        body.event = event;
    }
    if (customStageName) {
        body.custom_stage_name = customStageName;
    }
    if (customStyleName) {
        body.custom_style_name = customStyleName;
    }

    // 모델 설정 추가
    const modelConfig = getModelConfig('brief');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step1/brief', {
        method: 'POST',
        body: JSON.stringify(body)
    });

    currentSessionId = result.data.session_id;
    return result;
}

/**
 * Step 1: 브리프 피드백 반영 재생성
 */
async function refineBrief(currentBrief, feedback) {
    if (!currentSessionId) throw new APIError('세션이 없습니다', 'NO_SESSION');

    const body = {
        session_id: currentSessionId,
        current_brief: currentBrief,
        feedback: feedback
    };

    // 모델 설정 추가
    const modelConfig = getModelConfig('brief');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step1/brief/refine', {
        method: 'PUT',
        body: JSON.stringify(body)
    });

    return result;
}

// ===========================
// Step 2: Draft API
// ===========================

/**
 * Step 2: 초안 생성
 */
async function generateDraft(briefText) {
    if (!currentSessionId) throw new APIError('세션이 없습니다', 'NO_SESSION');

    const body = {
        session_id: currentSessionId,
        brief_text: briefText
    };

    // 모델 설정 추가
    const modelConfig = getModelConfig('draft');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step2/draft', {
        method: 'POST',
        body: JSON.stringify(body)
    });

    return result;
}

/**
 * Step 2: 초안 피드백 반영 재생성
 */
async function refineDraft(currentDraft, feedback) {
    if (!currentSessionId) throw new APIError('세션이 없습니다', 'NO_SESSION');

    const body = {
        session_id: currentSessionId,
        current_draft: currentDraft,
        feedback: feedback
    };

    // 모델 설정 추가
    const modelConfig = getModelConfig('draft');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step2/draft/refine', {
        method: 'PUT',
        body: JSON.stringify(body)
    });

    return result;
}

// ===========================
// Step 3: Tuning API
// ===========================

/**
 * Step 3: 페르소나별 메시지 생성 (선택한 페르소나만)
 */
async function generateTuning(draft, personas = null) {
    if (!currentSessionId) throw new APIError('세션이 없습니다', 'NO_SESSION');

    const body = {
        session_id: currentSessionId,
        draft: draft
    };

    // 선택된 페르소나 (null이면 기본 전체)
    if (personas && personas.length > 0) {
        body.personas = personas;
    }

    // 모델 설정 추가
    const modelConfig = getModelConfig('tuning');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step3/tuning', {
        method: 'POST',
        body: JSON.stringify(body)
    });

    return result;
}

/**
 * Step 3: 특정 페르소나 재생성
 */
async function refineTuning(persona, currentMessage, feedback) {
    if (!currentSessionId) throw new APIError('세션이 없습니다', 'NO_SESSION');

    const body = {
        session_id: currentSessionId,
        persona: persona,
        current_message: currentMessage,
        feedback: feedback
    };

    // 모델 설정 추가
    const modelConfig = getModelConfig('tuning');
    if (modelConfig) {
        body.model_config = modelConfig;
    }

    const result = await apiRequest('/step3/tuning/refine', {
        method: 'PUT',
        body: JSON.stringify(body)
    });

    return result;
}

// ===========================
// Health Check
// ===========================

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL.replace('/api/v1', '')}/health`);
        const data = await response.json();
        return data.status === 'ok';
    } catch {
        return false;
    }
}

// ===========================
// Export
// ===========================

window.CRMStudioAPI = {
    // Brief API
    generateBrief,
    refineBrief,
    
    // Draft API
    generateDraft,
    refineDraft,
    
    // Tuning API
    generateTuning,
    refineTuning,
    
    // Model & Provider API
    getAvailableModels,
    getPersonas,
    setModelConfig,
    getModelConfig,
    
    // Utility
    checkHealth,
    getSessionId: () => currentSessionId,
    resetSession: () => { 
        currentSessionId = null;
        availableModels = null;
    }
};
