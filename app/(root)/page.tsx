import InterviewCard from "@/components/InterviewCard";
import { Button } from "@/components/ui/button";
import { dummyInterview } from "@/constants";
import Image from "next/image";
import Link from "next/link";
import React from "react";

const page = () => {
  return (
    <>
      <section className="card-cta">
        <div className="flex flex-col gap-6 max-w-lg">
          <h2>Get Advice from AI-Powered expert</h2>
          <p className="text-lg">
            AI Advisor is an expert system that provides advice and solutions to
            everyday problems. It uses artificial intelligence to analyze data
            and provide recommendations based on the user input.
          </p>
          <Button asChild className="btn-primary max-sm:w-full">
            <Link href="/interview">Get Advice</Link>
          </Button>
        </div>
        <Image
          src="/robot.png"
          alt="robo-dude"
          width={400}
          height={400}
          className="max-sm:hidden"
        />
      </section>
      <section className="flex flex-col gap-6 mt-8">
        <h2>Your Questions</h2>
        <div className="interviews-section">
          {dummyInterview.map((interview) => (
            <div key={interview.id} className="interview-card">
             <InterviewCard {...interview} key={interview.id}/>
            </div>
          ))}
        </div>
      </section>
      <section className="flex flex-col gap-6 mt-8">
        <h2>Take an Interview</h2>
        <div className="interviews-section">
        {dummyInterview.map((interview) => (
            <div key={interview.id} className="interview-card">
             <InterviewCard {...interview} key={interview.id} />
            </div>
          ))}
        </div>
        {/* <p>No Interview as of yet </p> */}
      </section>
    </>
  );
};

export default page;
