import type { QuickAction } from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: "miranda",
    label: "Miranda Warning",
    query: "What are the Miranda warning requirements in Wisconsin?",
    icon: "Scale",
    description: "Rights advisement requirements",
  },
  {
    id: "owi",
    label: "OWI Elements",
    query: "What are the elements of an OWI offense under Wisconsin law?",
    icon: "Car",
    description: "Operating while intoxicated elements",
  },
  {
    id: "terry-stop",
    label: "Terry Stop Criteria",
    query: "What are the legal criteria for a Terry stop in Wisconsin?",
    icon: "Search",
    description: "Reasonable suspicion stop requirements",
  },
  {
    id: "use-of-force",
    label: "Use of Force Policy",
    query: "What is the use of force policy for Wisconsin law enforcement?",
    icon: "Shield",
    description: "Force continuum and policy guidelines",
  },
  {
    id: "vehicle-search",
    label: "Vehicle Search",
    query:
      "What are the legal requirements for searching a vehicle during a traffic stop in Wisconsin?",
    icon: "CarFront",
    description: "Vehicle search authority and requirements",
  },
  {
    id: "domestic-violence",
    label: "Domestic Violence",
    query:
      "What are the mandatory arrest requirements for domestic violence incidents in Wisconsin?",
    icon: "ShieldAlert",
    description: "DV mandatory arrest and procedures",
  },
  {
    id: "search-seizure",
    label: "Search & Seizure",
    query:
      "What are the Fourth Amendment search and seizure rules for Wisconsin law enforcement?",
    icon: "FileSearch",
    description: "Search warrant and exception requirements",
  },
  {
    id: "pursuit-policy",
    label: "Vehicle Pursuit",
    query:
      "What are the vehicle pursuit policies and legal requirements for Wisconsin law enforcement?",
    icon: "Siren",
    description: "Pursuit authorization and restrictions",
  },
];

export const STORAGE_KEY = "rag-conversations";

export const HEALTH_POLL_INTERVAL = 30_000;
