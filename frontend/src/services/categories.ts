import api from "./api";
import type { Category } from "../types/category";

export const categoriesApi = {
  list: () => api.get<Category[]>("/categories"),
};
