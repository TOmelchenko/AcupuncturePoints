import { z } from 'zod'

export const symptomSchema = z.object({
  symptom: z
    .string()
    .trim()
    .min(3, 'Please describe your symptom in a few words.')
    .max(1000, 'Please keep your description under 1,000 characters.'),
})

export const answerSchema = z.object({
  answer: z
    .string()
    .trim()
    .min(1, 'Please type an answer.')
    .max(1000, 'Please keep your answer under 1,000 characters.'),
})

export type SymptomValues = z.infer<typeof symptomSchema>
export type AnswerValues = z.infer<typeof answerSchema>
