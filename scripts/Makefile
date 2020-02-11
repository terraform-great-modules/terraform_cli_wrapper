# Copyright 2016 Philip G. Porada
# Copyright 2020 Riccardo Scartozzi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

MAKEFILE_VERSION := 0.1.0

.ONESHELL:
.SHELL := /usr/bin/bash
.SHELLFLAGS = -ec  # NB: c is strictly required
.PHONY: apply destroy-backend destroy destroy-target plan-destroy plan plan-target prep install console
.PHONY: list-providers list-modules list-resources

CURRENT_FOLDER=$(shell basename "$$(pwd)")
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))

#include ../makefile.variables
ifeq ($(wildcard makefile.variables),makefile.variables)
  include makefile.variables
endif

# Input variables
TMP_FOLDER ?= /tmp/terraform
LOCAL_BIN ?= $(TMP_FOLDER)/bin
TF_TARGET_VERSION  ?= 0.12.20
TF_LOCAL_BIN ?= $(LOCAL_BIN)/terraform
TF_PLUGIN_UPGRADE ?= true  #o# If false do not refresh plugins
TF_VARS_FILE ?= 
ifeq (,$(TF_VARS_FILE))
  TF_VARS ?= 
else
  TF_VARS ?= '-var-file="$(TF_VARS_FILE)"'
endif
TF_LOG ?= 
REGION ?= ''
S3_REGION ?= $(REGION)
WORKFLOW ?= 
PROJECT_STREAM ?= $(CURRENT_FOLDER)
PROJECT ?= $(WORKFLOW)-$(PROJECT_STREAM)
TMP_WF_FOLDER ?= $(TMP_FOLDER)/$(WORKFLOW)
TMP_PR_FOLDER ?= $(TMP_FOLDER)/$(WORKFLOW)/$(PROJECT_STREAM)
USE_SSH_KEY ?= true  #o# Set to false is a pair of ssh key in not required for administering local resources
SSH_KEY ?= $(WORKFLOW)_key
SSH_PATH ?= $(TMP_WF_FOLDER)/.ssh
S3_BUCKET ?= tools-services
S3_FOLDER ?= $(PROJECT)/$(REGION)
DYNAMODB_TABLE ?= tools-services-terraform

ifneq ($(AWS_CHECKS),false)  #o# If false, do not check AWS deps like: dynamodb and s3 backend, ssh keys
  AWSDEPS := aws-deps
endif
tmp_mkdir := $(TMP_FOLDER) $(TMP_WF_FOLDER) $(TMP_PR_FOLDER)
##
# TERRAFORM INSTALL
##
TERRAFORM_INSTALL  ?= true
TF_SYSTEM_BIN      ?= $(shell command -v terraform 2> /dev/null)
ifneq (,$(TF_SYSTEM_BIN))
  ifneq ($(shell $(TF_SYSTEM_BIN) -version | head -n 1 | grep -Po '(?<=Terraform v)[^;]+'),$(TF_TARGET_VERSION))
    TF ?= $(shell ls $(TF_LOCAL_BIN) 2> /dev/null || echo $(TF_SYSTEM_BIN))
  else
    TF ?= $(TF_SYSTEM_BIN)
  endif
endif
ifneq (,$(TF))
  TF_VERSION := $(shell $(TF) -version | head -n 1 | grep -Po '(?<=Terraform v)[^;]+')
endif
TF_ZIP ?= $(TMP_FOLDER)/terraform_$(TF_TARGET_VERSION).zip
  

#WORKSPACE="$(ENV)-$(REGION)"
# Shell colors
BOLD=$(shell tput bold)
RED=$(shell tput setaf 1)
GREEN=$(shell tput setaf 2)
YELLOW=$(shell tput setaf 3)
RESET=$(shell tput sgr0)
# Shell alias
AWS=aws --profile $(AWS_PROFILE)



help:
	@echo "Welcome to the smart terraform wrapper!"
	echo ""
	echo "List of commands:"
	grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo ""
	echo "List of common options:"
	grep -h -E '^[a-zA-Z_-]+.*?#o# .*$$' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = " *?#o# "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

print-%:  # Alias for variable printing (just invoke as 'make print-VAR_NAME')
	@echo $*=$($*)


list-providers:  ## List providers in use
	@find . -type f -iname "*.tf" -exec \
	  awk '
	  BEGIN {print "List of providers and versions:"}
	  / *provider +".*"/ {
	        PROV = $$2;
	        while ($$0!~/^[^#]*}/)
		      {if ($$0~/^ *version/) match($$0,/version.*= *"(.+)" */,VER);
	               getline;};
	        print "  ", PROV, " is " VER[1]}' {} +
	$(TF) providers

list-modules:  ## List required modules
	@find . -type f -iname "*.tf" -exec \
	  awk '  
	  BEGIN {print "List of modules and required sources:"} 
	  / *module +".*"/ { 
	        USEDBY = USEDBY ", " $$2; 
	        while ($$0!~/^[^#]*}/)
		{if ($$0~/^ *source/) match($$0,/ *source *= *"(.+)" */,SOURCE) ;
	               getline ; };
	        print "  ", SOURCE[1], " used by ", USEDBY }' {} +

list-resources:  ## List resources generated
	@$(TF) state list

$(tmp_mkdir):
	@mkdir -p $@


set-env: install
	@echo "Working into folder $(mkfile_path)"
	if [ -z "$(REGION)" ]; then \
	  echo "$(BOLD)$(RED)REGION was not set$(RESET)"; \
	  ERROR=1; fi
	if [ -z "$(AWS_PROFILE)" ]; then \
	  echo "$(BOLD)$(RED)AWS_PROFILE was not set.$(RESET)"; \
	  ERROR=1; fi
	if [ ! -z $${ERROR} ] && [ $${ERROR} -eq 1 ]; then \
	  echo "$(BOLD)Example usage: \`AWS_PROFILE=whatever REGION=us-east-2 make plan\`$(RESET)"; \
	  exit 1; fi
#	@if [ ! -f "$(VARS)" ]; then \
#	  echo "$(BOLD)$(RED)Could not find variables file: $(VARS)$(RESET)"; \
#	  exit 1; fi


.PHONY: terraform_install
terraform_install: $(tmp_mkdir)
ifeq ($(TF_VERSION),$(TF_TARGET_VERSION))
	@echo "Terraform is updated to wanted version $(TF_TARGET_VERSION)"
else
   ifneq ($(TERRAFORM_INSTALL),true)
      ifneq (,$(TF))
	@echo "$(BOLD)$(RED)Terraform version is not the same as wanted!"
	echo "Wanted: $(TF_TARGET_VERSION), " \
	  "available: $$(terraform -version | head -n 1 | grep -Po '(?<=Terraform v)[^;]+')$(RESET)"
      else
	@echo "$(BOLD)$(RED)Could not find a Terraform executable, enable TERRAFORM_INSTALL=true to locally download$(RESET)"
      endif
	exit 1
   else
	@arch=$$(case $$(uname -m) in \
	    x86_64)  echo "amd64";; \
	    i686)    echo "386";; \
	    aarch64) echo "arm";; \
	  esac)
	url='https://releases.hashicorp.com/terraform/$(TF_TARGET_VERSION)'
	filename=terraform_$(TF_TARGET_VERSION)_$$(uname|tr A-Z a-z)_$${arch}.zip
	wget -O $(TF_ZIP) $${url}/$${filename} || exit 1
	unzip -o -d $(LOCAL_BIN) $(TF_ZIP) && rm $(TF_ZIP)
	$(eval TF := $(TF_LOCAL_BIN))
   endif
endif

.PHONY: full_install
full_install: terraform_install
	@$(TF) -version

install: full_install ## Install the terraform binary and set the landscape utility


.PHONY: aws-deps
aws-deps: # check aws dependency for S3 and dynamodb and ssh keys
	@echo "$(BOLD)Verifying that the S3 bucket $(S3_BUCKET) " \
	      "for remote state exists$(RESET)"
	$(AWS) s3api head-bucket --region $(S3_REGION) --bucket $(S3_BUCKET) > /dev/null 2>&1 && \
	     echo "$(BOLD)$(GREEN)S3 bucket $(S3_BUCKET) exists$(RESET)" || \
	     (echo "$(BOLD)S3 bucket $(S3_BUCKET) was not found, creating new bucket with versioning enabled to store tfstate$(RESET)"; \
	      $(AWS) s3api create-bucket \
	          --bucket $(S3_BUCKET) \
	          --acl private \
	          --region $(S3_REGION) \
	          --create-bucket-configuration LocationConstraint=$(S3_REGION) > /dev/null 2>&1 ; \
	      $(AWS) s3api put-bucket-versioning \
	          --bucket $(S3_BUCKET) \
	          --versioning-configuration Status=Enabled > /dev/null 2>&1 ; \
	      echo "$(BOLD)$(GREEN)S3 bucket $(S3_BUCKET) created$(RESET)")
	echo "$(BOLD)Verifying that the DynamoDB table exists for remote state locking$(RESET)"
	$(AWS) dynamodb describe-table --region $(S3_REGION) --table-name $(DYNAMODB_TABLE) > /dev/null 2>&1 && \
	     echo "$(BOLD)$(GREEN)DynamoDB Table $(DYNAMODB_TABLE) exists$(RESET)" || \
	     (echo "$(BOLD)DynamoDB table $(DYNAMODB_TABLE) was not found, " \
	           "creating new DynamoDB table to maintain locks$(RESET)"; \
	      $(AWS) dynamodb create-table \
	          --region $(S3_REGION) \
	          --table-name $(DYNAMODB_TABLE) \
	          --attribute-definitions AttributeName=LockID,AttributeType=S \
	          --key-schema AttributeName=LockID,KeyType=HASH \
	          --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 > /dev/null 2>&1 ; \
	      echo "$(BOLD)$(GREEN)DynamoDB table $(DYNAMODB_TABLE) created$(RESET)"; \
	      echo "Sleeping for 10 seconds to allow DynamoDB state to propagate through AWS"; \
	      sleep 10)
ifneq (false,$(USE_SSH_KEY))
	if $(AWS) --region $(REGION) ec2 describe-key-pairs | jq -r '.KeyPairs[].KeyName' | grep "$(SSH_KEY)" > /dev/null 2>&1; then
	  if [ ! -f "$(SSH_PATH)/$(SSH_KEY)" ]; then \
	    $(AWS) s3 cp s3://$(S3_BUCKET)/$(S3_FOLDER)/$(SSH_KEY).pub $(SSH_PATH)/$(SSH_KEY).pub; \
	    $(AWS) s3 cp s3://$(S3_BUCKET)/$(S3_FOLDER)/$(SSH_KEY) $(SSH_PATH)/$(SSH_KEY); fi; \
	else
	  echo "$(BOLD)$(RED)EC2 Key Pair $(SSH_KEY) was not found$(RESET)"; \
	  read -p '$(BOLD)Do you want to generate a new keypair? [y/Y]: $(RESET)' ANSWER && \
	  if [ "$${ANSWER}" = "y" ] || [ "$${ANSWER}" = "Y" ]; then \
	    mkdir -p $(SSH_PATH); \
	    ssh-keygen -t rsa -b 4096 -N '' -f $(SSH_PATH)/$(SSH_KEY); \
	    $(AWS) ec2 import-key-pair \
	        --region $(REGION) \
	        --key-name "$(SSH_KEY)" \
	        --public-key-material "file://$(SSH_PATH)/$(SSH_KEY).pub"; \
	    $(AWS) s3 cp $(SSH_PATH)/$(SSH_KEY).pub s3://$(S3_BUCKET)/$(S3_FOLDER)/$(SSH_KEY).pub; \
	    $(AWS) s3 cp $(SSH_PATH)/$(SSH_KEY) s3://$(S3_BUCKET)/$(S3_FOLDER)/$(SSH_KEY); fi; fi
	echo "$(BOLD)$(GREEN)EC2 Key Pair $(SSH_KEY)$(RESET)"
endif


prep: set-env $(AWSDEPS) ## Prepare a new workspace (environment) if needed, configure the tfstate backend, update any modules, and switch to the workspace
	@echo "$(BOLD)Configuring the terraform backend$(RESET)"
	[ "$(TF_PLUGIN_UPGRADE)" = "true" ] && TF_PLUGIN_UPGRADE=" -upgrade=true " || TF_PLUGIN_UPGRADE=" -upgrade=false "
	$(TF) init -input=false \
	           -force-copy \
	           -lock=true \
	           $${TF_PLUGIN_UPGRADE} \
	           -verify-plugins=true \
	           -backend=true \
	           -backend-config="profile=$(AWS_PROFILE)" \
	           -backend-config="region=$(S3_REGION)" \
	           -backend-config="bucket=$(S3_BUCKET)" \
	           -backend-config="key=$(S3_FOLDER)/terraform.tfstate" \
	           -backend-config="dynamodb_table=$(DYNAMODB_TABLE)"\
	           -backend-config="acl=private"
	echo "$(BOLD)Terraform ready!$(RESET)"
	#@echo "$(BOLD)Switching to workspace $(WORKSPACE)$(RESET)"
	#@terraform workspace select $(WORKSPACE) || terraform workspace new $(WORKSPACE)

console: prep ## Show what terraform thinks it will do
	$(TF) console

plan: prep ## Show what terraform thinks it will do
	$(TF_LOG) $(TF) plan \
	    -lock=true \
	    -input=false \
	    -refresh=true $(TF_VARS)

plan-target: prep ## Shows what a plan looks like for applying a specific resource
	@echo "$(YELLOW)$(BOLD)[INFO]   $(RESET)"; echo "Example to type for the following question: module.rds.aws_route53_record.rds-master"
	read -p "PLAN target: " DATA && \
		$(TF) plan \
			-lock=true \
			-input=true \
			-refresh=true $(TF_VARS)
			-target=$$DATA

plan-destroy: prep ## Creates a destruction plan.
	@$(TF) plan \
		-input=false \
		-refresh=true \
		-destroy $(TF_VARS)

apply: prep ## Have terraform do the things. This will cost money.
	@$(TF) apply \
		-lock=true \
		-input=false \
		-refresh=true $(TF_VARS)

destroy: prep ## Destroy the things
	@$(TF) destroy \
		-lock=true \
		-input=false \
		-refresh=true $(TF_VARS)

destroy-target: prep ## Destroy a specific resource. Caution though, this destroys chained resources.
	@echo "$(YELLOW)$(BOLD)[INFO] Specifically destroy a piece of Terraform data.$(RESET)"
	echo "Example to type for the following question: module.rds.aws_route53_record.rds-master"
	read -p "Destroy target: " DATA && \
		$(TF) destroy \
		-lock=true \
		-input=false \
		-refresh=true $(TF_VARS) \
		-target=$$DATA

destroy-backend: ## Destroy S3 bucket and DynamoDB table
	@if ! $(AWS) dynamodb delete-table \
		--region $(REGION) \
		--table-name $(DYNAMODB_TABLE) > /dev/null 2>&1 ; then \
			echo "$(BOLD)$(RED)Unable to delete DynamoDB table $(DYNAMODB_TABLE)$(RESET)"; \
	 else
		echo "$(BOLD)$(RED)DynamoDB table $(DYNAMODB_TABLE) does not exist.$(RESET)"; \
	 fi
	@if ! $(AWS) s3api delete-objects \
		--region $(REGION) \
		--bucket $(S3_BUCKET) \
		--delete "$$($(AWS) s3api list-object-versions \
						--region $(REGION) \
						--bucket $(S3_BUCKET) \
						--output=json \
						--query='{Objects: Versions[].{Key:Key,VersionId:VersionId}}')" > /dev/null 2>&1 ; then \
			echo "$(BOLD)$(RED)Unable to delete objects in S3 bucket $(S3_BUCKET)$(RESET)"; \
	 fi
	@if ! $(AWS) s3api delete-objects \
		--region $(REGION) \
		--bucket $(S3_BUCKET) \
		--delete "$$($(AWS) s3api list-object-versions \
						--region $(REGION) \
						--bucket $(S3_BUCKET) \
						--output=json \
						--query='{Objects: DeleteMarkers[].{Key:Key,VersionId:VersionId}}')" > /dev/null 2>&1 ; then \
			echo "$(BOLD)$(RED)Unable to delete markers in S3 bucket $(S3_BUCKET)$(RESET)"; \
	 fi
	#@if ! $(AWS) s3api delete-bucket \
	#	--region $(REGION) \
	#	--bucket $(S3_BUCKET) > /dev/null 2>&1 ; then \
	#		echo "$(BOLD)$(RED)Unable to delete S3 bucket $(S3_BUCKET) itself$(RESET)"; \
	# fi

.PHONY: version
version:  ## Get current Makefile version
	@echo $(MAKEFILE_VERSION)
