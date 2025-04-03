import React from "react";
import dayjs from "dayjs";
import Image from "next/image";

import { Button } from "./ui/button";
import Link from "next/link";
import { getRandomInterviewCover } from "@/lib/utils";
import DisplayTechIcons from "./DisplayTechIcons";

const InterviewCard = ({
  interviewId,
  userId,
  role,
  type,
  techstack,
  createdAt,
}: InterviewCardProps) => {
  const feedback = null as Feedback | null;
  const normalizedType = /mix/gi.test(type) ? "Mix" : type;
  const formattedDate = dayjs(
    feedback?.createdAt || createdAt || Date.now()
  ).format("MMM DD, YYYY");

  return (
    <div className="card-border w-[360px] max-sm:w-full min-h-96 ">
      <div className="card-interview">
        <div>
          <div className="absolute top-0 right-0 w-fit px-4 py-2 rounded-bl-lg bg-light-600 justify-end">
            <p className="badge-text">{normalizedType}</p>
          </div>
        </div>
        <Image
          src={getRandomInterviewCover()}
          alt="cover image"
          width={90}
          height={90}
          className="rounded-full object-fill size-[90px]"
        />
        <h3 className="mt-5 capitalize">
           {role} interview 
        </h3>
        <div className="flex flex-row gap-5 mt-3">
            <div className="flex flex-row gap-2">
                <Image src="/calendar.svg" alt="calendar" width={16} height={16} />
                <p>{formattedDate}</p>
                <div className="flex flex-row gap-2">
                    <Image src="/star.svg" alt="star" width={16} height={16} />
                    <p>{feedback?.totalScore ||  '---'}/100</p>
                </div>
            </div>
            <p className="line-clamp-2 mt-5">
                {feedback?.finalAssessment || 'No feedback yet'}
            </p>
        </div>
        <div className="flex flex-row justify-between">
            <DisplayTechIcons techstack={techstack} />
            <Button className="btn-primary">
                <Link href={feedback ? `/interview/${interviewId}/feedback` : `/interview/${interviewId}`}>
                    {feedback ? 'View Feedback' : 'Start Interview'}
                </Link>
            </Button>
        </div>
      </div>
    </div>
  );
};

export default InterviewCard;
