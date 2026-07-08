export function normalizeAgreementTerm(text: string): string {
  return text.replace(/\u5408\u540c/g, '\u5408\u7ea6')
}
