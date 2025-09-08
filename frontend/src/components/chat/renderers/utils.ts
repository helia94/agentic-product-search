export const isHtmlContent = (content: string): boolean => {
  const htmlPattern = /<!DOCTYPE html>|<html[^>]*>|<\/html>/i;
  return htmlPattern.test(content.trim());
};