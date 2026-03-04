import api from "./api";
import type {
  UserWithToken,
  SurveyList,
  SurveyDetail,
  PaperList,
  ChatResponse,
} from "@/types";

// ---- Auth ----
export const authApi = {
  register: (data: { email: string; password: string; full_name: string }) =>
    api.post<UserWithToken>("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post<UserWithToken>("/auth/login", data),

  refresh: (refresh_token: string) =>
    api.post("/auth/refresh", { refresh_token }),

  getMe: () => api.get<UserWithToken["user"]>("/auth/me"),
};

// ---- Surveys ----
export const surveyApi = {
  create: (topic: string) =>
    api.post<SurveyDetail>("/surveys", { topic }),

  list: (skip = 0, limit = 20) =>
    api.get<SurveyList>("/surveys", { params: { skip, limit } }),

  get: (surveyId: string) =>
    api.get<SurveyDetail>(`/surveys/${surveyId}`),

  delete: (surveyId: string) =>
    api.delete(`/surveys/${surveyId}`),
};

// ---- Papers ----
export const paperApi = {
  list: (surveyId: string) =>
    api.get<PaperList>(`/surveys/${surveyId}/papers`),
};

// ---- Chat ----
export const chatApi = {
  send: (surveyId: string, message: string) =>
    api.post<ChatResponse>(`/surveys/${surveyId}/chat`, { message }),
};
