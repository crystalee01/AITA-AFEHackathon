# -*- coding: utf-8 -*-

import logging
import ask_sdk_core.utils as ask_utils
import os
from ask_sdk_s3.adapter import S3Adapter
s3_adapter = S3Adapter(bucket_name=os.environ["S3_PERSISTENCE_BUCKET"])
import boto3
s3 = boto3.client('s3')
s3Resource = boto3.resource('s3')
import json

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_core.utils import is_request_type, is_intent_name

from ask_sdk_model.interfaces.audioplayer import (
    PlayDirective, PlayBehavior, AudioItem, Stream)

from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello, I am AITA, your Artificial Intelligence Teaching Assistant. What would you like to do today? You can set up a work time, start a work time, or set music"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

class CaptureMusicPreferenceIntentHandler(AbstractRequestHandler):
    """Handler for capturing WorkType Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CaptureMusicPreferenceIntent")(handler_input)
        
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        musicPreference = slots["musicPreference"].value
        
        url = ""
        if "white" in musicPreference: url = "https://sndup.net/5t9x/Pink+10m+%28mp3cutnet%29.mp3"
        else: url = "https://sndup.net/3qhy/Homework+%28mp3cutnet%29.mp3"
        
        data = {}
        data["musicPreference"] = url
        jsonString = json.dumps(data)
        encodedData = jsonString.encode('utf-8')
        
        s3Key = "Media/musicPreference.txt"
        s3.put_object(Body=encodedData, Bucket='391494fe-6b75-43db-89eb-a22dad514b56-us-east-1', Key=s3Key)
        
        speak_output = "I've set your music preference to " + musicPreference
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )
    

class CaptureWorktypeIntentHandler(AbstractRequestHandler):
    """Handler for capturing WorkType Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CaptureWorktypeIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        worktypeName = slots["worktypeName"].value
        workDuration = slots["workDuration"].value
        
        worktypeNameKey = worktypeName + "_NAME"
        workDurationKey = worktypeName + "_DURATION"
        data = {}
        data[worktypeNameKey] = worktypeName
        data[workDurationKey] = workDuration
        jsonString = json.dumps(data)
        encodedData = jsonString.encode('utf-8')
        fileName = worktypeName + ".txt"
        
        s3Key = "Media/worktypes/" + fileName
        s3.put_object(Body=encodedData, Bucket='391494fe-6b75-43db-89eb-a22dad514b56-us-east-1', Key=s3Key)
        
        timeLen = getWorkDuration(workDuration)
        durationInSpeech = convertPTTimeToSpeech(int(timeLen), workDuration)
        speak_output = "I've created your " + worktypeName + "timer for " + timeLen + durationInSpeech

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )

class StartWorktypeIntentHandler(AbstractRequestHandler):
    """Handler for StartWorktype Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_intent_name("StartWorktypeIntent")(handler_input)
        
    def handle(self, handler_input): 
        # type: (HandlerInput) -> Response
        slots = handler_input.request_envelope.request.intent.slots
        worktypeName = slots["worktypeName"].value
        fileName = worktypeName + ".txt"
        
        s3Key = "Media/worktypes/" + fileName
        obj = s3.get_object(Bucket='391494fe-6b75-43db-89eb-a22dad514b56-us-east-1', Key=s3Key)
        data = obj['Body'].read()
        contents = data.decode('utf-8') 
        dataDict = json.loads(contents)

        workDurationKey = worktypeName + "_DURATION"
        workDuration = dataDict[workDurationKey] 
        
        # invoke timer API here 
        
        # prompt music 
        
        timeLen = getWorkDuration(workDuration)
        timeUnits = convertPTTimeToSpeech(int(timeLen), workDuration)
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr["duration"] = int(timeLen) # duration converted from string -> #
        session_attr["work_type"] = worktypeName
        speak_output = "Your " + timeLen + timeUnits + "of " + worktypeName + " starts now"

        return (
            handler_input.response_builder
                .speak("Ok would you like music during your session?")
                .ask("Ok would you like music during your session?")
                .response
        )

class YesOrNoIntentHandler(AbstractRequestHandler):
    """Single handler for Yes and No Intent."""
    
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input))
    
    def handle(self, handler_input):
        session_attr = handler_input.attributes_manager.session_attributes
        duration = session_attr["duration"]
        # work_type = session_attr["work_type"]
        if(ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)):
            return Controller.play(handler_input, duration, True)
        else:
            return Controller.play(handler_input, duration, False)


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "How can I help?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble doing what you asked. Please try again."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class StartPlaybackHandler(AbstractRequestHandler):
    """Handler for Playing audio on different events.
    Handles PlayAudio Intent, Resume Intent.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (is_intent_name("AMAZON.ResumeIntent")(handler_input)
                or is_intent_name("PlayAudio")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In StartPlaybackHandler")
        return Controller.play(handler_input, 1, True)


class PlaybackNearlyFinishedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackNearlyFinished Directive received.
    Replacing queue with the URL again. This should not happen on live streams.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackNearlyFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackNearlyFinishedHandler")
        return Controller.enqueue(handler_input)

class PlaybackFinishedEventHandler(AbstractRequestHandler):
    """AudioPlayer.PlaybackFinished Directive received.
    Do not send any specific response.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return is_request_type("AudioPlayer.PlaybackFinished")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In PlaybackFinishedHandler")

        return handler_input.response_builder.response


class Controller:
    """Audioplayer and Playback Controller."""
    @staticmethod
    def play(handler_input, num_minutes, with_music):
        # type: (HandlerInput) -> Response
        logger.info("In Controller.play with "+str(num_minutes))
        response_builder = handler_input.response_builder

        play_behavior = PlayBehavior.REPLACE_ALL

        if with_music:
            s3Key = "Media/musicPreference.txt"
            obj = s3.get_object(Bucket='391494fe-6b75-43db-89eb-a22dad514b56-us-east-1', Key=s3Key)
            data = obj['Body'].read()
            contents = data.decode('utf-8') 
            dataDict = json.loads(contents)

            musicUrl = dataDict["musicPreference"] 

            response_builder.add_directive(
                PlayDirective(
                    play_behavior=play_behavior,
                    audio_item=AudioItem(
                        stream=Stream(
                            token="M "+str(num_minutes),
                            url=musicUrl,
                            offset_in_milliseconds=0,
                            expected_previous_token=None),
                        metadata=None))
            ).set_should_end_session(True)
            response_builder.speak("Ok, playing study music")
        else:
            response_builder.add_directive(
                PlayDirective(
                    play_behavior=play_behavior,
                    audio_item=AudioItem(
                        stream=Stream(
                            token="S "+str(num_minutes),
                            url="https://sndup.net/7n44/1-minute-of-silence.mp3",
                            offset_in_milliseconds=0,
                            expected_previous_token=None),
                        metadata=None))
            ).set_should_end_session(True)
            response_builder.speak("Ok, I will let you know when your timer is over.")

        return response_builder.response

    @staticmethod
    def enqueue(handler_input):
        # type: (HandlerInput) -> Response
        response_builder = handler_input.response_builder
        type, cur_num = handler_input.request_envelope.request.token.split(' ')
        logger.info("In Controller.enqueue with "+cur_num)
        
        if(int(cur_num)<1):
            logger.info("Finish")
            return handler_input.response_builder.response

        play_behavior = PlayBehavior.ENQUEUE
        
        if(int(cur_num)==1):
            logger.info("Enqueue for final file")
            response_builder.add_directive(
                PlayDirective(
                    play_behavior=play_behavior,
                    audio_item=AudioItem(
                        stream=Stream(
                            token=type+" "+str((int(cur_num)-1)),
                            url="https://sndup.net/6vgx/Fri+Jul+24+2020+%28mp3cutnet%29.mp3",
                            offset_in_milliseconds=0,
                            expected_previous_token=handler_input.request_envelope.request.token),
                        metadata=None))
            )
        elif(type=="M"):
            logger.info("Enqueue for sound file")
            response_builder.add_directive(
                PlayDirective(
                    play_behavior=play_behavior,
                    audio_item=AudioItem(
                        stream=Stream(
                            token=type+" "+str((int(cur_num)-1)),
                            url="https://sndup.net/3qhy/Homework+%28mp3cutnet%29.mp3",
                            offset_in_milliseconds=0,
                            expected_previous_token=handler_input.request_envelope.request.token),
                        metadata=None))
            )
        else:
            logger.info("Enqueue for silent file")
            response_builder.add_directive(
                PlayDirective(
                    play_behavior=play_behavior,
                    audio_item=AudioItem(
                        stream=Stream(
                            token=type+" "+str((int(cur_num)-1)),
                            url="https://sndup.net/7n44/1-minute-of-silence.mp3",
                            offset_in_milliseconds=0,
                            expected_previous_token=handler_input.request_envelope.request.token),
                        metadata=None))
            )

        return response_builder.response


def getWorkDuration(workDuration):
    # string of Amazon.DURATION -> string of time length
    timestamp = "PT"
    units = ""
    unitIndex = len(timestamp)

    timeLen = workDuration[len(timestamp):len(workDuration) - 1]
    return timeLen


def convertPTTimeToSpeech(numDuration, workDuration):
    # string of Amazon.DURATION -> string of time units
    units = ""
    if "M" in workDuration: 
        units = " minute"
    elif "H" in workDuration: 
        units = " hour"
    
    if numDuration > 1: return units + "s "
    return units + " "


class ExceptionEncounteredHandler(AbstractRequestHandler):
    """Handler to handle exceptions from responses sent by AudioPlayer
    request.
    """
    def can_handle(self, handler_input):
        # type; (HandlerInput) -> bool
        return is_request_type("System.ExceptionEncountered")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In ExceptionEncounteredHandler")
        logger.info("System exception encountered: {}".format(
            handler_input.request_envelope.request))
        return handler_input.response_builder.response

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

sb = CustomSkillBuilder(persistence_adapter=s3_adapter)

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(StartPlaybackHandler())
sb.add_request_handler(PlaybackNearlyFinishedEventHandler())
sb.add_request_handler(CaptureWorktypeIntentHandler())
sb.add_request_handler(StartWorktypeIntentHandler())
sb.add_request_handler(PlaybackFinishedEventHandler())
sb.add_request_handler(ExceptionEncounteredHandler())
sb.add_request_handler(YesOrNoIntentHandler())
sb.add_request_handler(CaptureMusicPreferenceIntentHandler())
# sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())


lambda_handler = sb.lambda_handler()